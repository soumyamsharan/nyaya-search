"""Retrieval: BM25, vector and hybrid retrievers behind one interface, plus the search service on top."""

import re
from collections.abc import Sequence
from typing import Protocol

from nyaya.db import Database
from nyaya.domain import (
    Outcome,
    SearchFilters,
    SearchHit,
    SearchMode,
    SearchResponse,
    SearchResult,
)
from nyaya.errors import InvalidRequestError
from nyaya.ml import Embedder, Reranker
from nyaya.repos import CitationRepository, JudgmentRepository
from nyaya.text import ParsedQuery, is_citation_query, normalize_act, normalize_citation, parse_query

RRF_K = 60
NO_RESULTS = "No relevant judgments found."
NOT_IN_CORPUS = "That judgment is not in the corpus."


class Retriever(Protocol):
    def retrieve(self, query: ParsedQuery, filters: SearchFilters, limit: int) -> list[SearchHit]: ...


# Dataset disposal values grouped into the outcomes users filter by. Anything else (or empty) is "other".
OUTCOME_VALUES: dict[Outcome, list[str]] = {
    Outcome.ALLOWED: ["Appeal(s) allowed", "Case Allowed"],
    Outcome.PARTLY_ALLOWED: ["Case Partly allowed"],
    Outcome.DISMISSED: ["Dismissed", "Rejected"],
    Outcome.DISPOSED: ["Disposed off", "IA disposed"],
}


def filter_sql(filters: SearchFilters) -> tuple[str, dict]:
    """SQL conditions on judgments j / paragraphs p for the given filters (parameterised)."""
    conditions = ["j.status = 'ok'"]
    params: dict = {}
    if filters.year_from is not None:
        conditions.append("j.decision_date >= make_date(%(year_from)s, 1, 1)")
        params["year_from"] = filters.year_from
    if filters.year_to is not None:
        conditions.append("j.decision_date < make_date(%(year_to)s + 1, 1, 1)")
        params["year_to"] = filters.year_to
    if filters.date_from is not None:
        conditions.append("j.decision_date >= %(date_from)s")
        params["date_from"] = filters.date_from
    if filters.date_to is not None:
        conditions.append("j.decision_date <= %(date_to)s")
        params["date_to"] = filters.date_to
    judges = [*filters.judges, *([filters.judge] if filters.judge else [])]
    for i, judge in enumerate(j.strip() for j in judges if j.strip()):
        conditions.append(f"EXISTS (SELECT 1 FROM unnest(j.bench) b WHERE b ILIKE %(judge{i})s)")
        params[f"judge{i}"] = f"%{judge}%"
    if filters.author:
        conditions.append("j.author ILIKE %(author)s")
        params["author"] = f"%{filters.author.strip()}%"
    if filters.outcome == Outcome.OTHER:
        conditions.append("(j.disposal_nature IS NULL OR NOT (j.disposal_nature = ANY(%(known_outcomes)s)))")
        params["known_outcomes"] = [v for values in OUTCOME_VALUES.values() for v in values]
    elif filters.outcome:
        conditions.append("j.disposal_nature = ANY(%(outcome)s)")
        params["outcome"] = OUTCOME_VALUES[filters.outcome]
    if filters.roles:
        conditions.append("p.role = ANY(%(roles)s)")
        params["roles"] = [r.value for r in filters.roles]
    if filters.act or filters.section:
        act_condition = ["a.judgment_id = j.id"]
        if filters.act:
            act_condition.append("a.act_norm LIKE %(act)s")
            params["act"] = f"%{normalize_act(filters.act)}%"
        if filters.section:
            act_condition.append("a.section = %(section)s")
            params["section"] = filters.section.strip().upper()
        conditions.append(f"EXISTS (SELECT 1 FROM judgment_acts a WHERE {' AND '.join(act_condition)})")
    if filters.judgment_id:
        conditions.append("p.judgment_id = %(judgment_id)s")
        params["judgment_id"] = filters.judgment_id
    return " AND ".join(conditions), params


def term_pattern(term: str) -> str:
    """Case-insensitive whole-word Postgres regex for a word or phrase (any whitespace between words)."""
    body = r"\s+".join(re.escape(word) for word in term.split())
    start = r"\m" if term[:1].isalnum() else ""
    end = r"\M" if term[-1:].isalnum() else ""
    return f"{start}{body}{end}"


def term_sql(query: ParsedQuery) -> tuple[str, dict]:
    """Required (AND, quoted) and excluded (NOT) terms as SQL on paragraphs p, shared by every retriever."""
    conditions, params = [], {}
    for i, term in enumerate(query.required):
        conditions.append(f"p.text ~* %(req{i})s")
        params[f"req{i}"] = term_pattern(term)
    for i, term in enumerate(query.excluded):
        conditions.append(f"p.text !~* %(exc{i})s")
        params[f"exc{i}"] = term_pattern(term)
    return " AND ".join(conditions) or "TRUE", params


def _hits(rows: list[dict]) -> list[SearchHit]:
    return [SearchHit(paragraph_id=r["id"], judgment_id=r["judgment_id"], score=float(r["score"])) for r in rows]


class Bm25Retriever:
    def __init__(self, db: Database) -> None:
        self._db = db

    def retrieve(self, query: ParsedQuery, filters: SearchFilters, limit: int) -> list[SearchHit]:
        if not query.rerank_text:
            return []
        where, params = filter_sql(filters)
        terms, term_params = term_sql(query)
        params |= term_params | {"q": query.rerank_text, "limit": limit}
        rows = self._db.fetch_all(
            f"""SELECT p.id, p.judgment_id, paradedb.score(p.id) AS score
                FROM paragraphs p JOIN judgments j ON j.id = p.judgment_id
                WHERE p.text ||| %(q)s AND {terms} AND {where}
                ORDER BY score DESC LIMIT %(limit)s""",
            params,
        )
        return _hits(rows)


class VectorRetriever:
    def __init__(self, db: Database, embedder: Embedder) -> None:
        self._db = db
        self._embedder = embedder

    def retrieve(self, query: ParsedQuery, filters: SearchFilters, limit: int) -> list[SearchHit]:
        text = query.rerank_text
        if not text:
            return []
        vector = self._embedder.embed([text])[0]
        where, params = filter_sql(filters)
        terms, term_params = term_sql(query)
        where = f"{where} AND {terms}"
        params |= term_params | {"v": "[" + ",".join(f"{x:.6f}" for x in vector) + "]", "limit": limit}
        with self._db.connection() as conn, conn.transaction():
            conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
            conn.execute("SET LOCAL hnsw.ef_search = 200")
            rows = conn.execute(
                f"""SELECT p.id, p.judgment_id, 1 - (p.embedding <=> %(v)s::halfvec) AS score
                    FROM paragraphs p JOIN judgments j ON j.id = p.judgment_id
                    WHERE p.embedding IS NOT NULL AND {where}
                    ORDER BY p.embedding <=> %(v)s::halfvec LIMIT %(limit)s""",
                params,
            ).fetchall()
        return _hits(rows)


def reciprocal_rank_fusion(rankings: Sequence[list[SearchHit]], k: int = RRF_K) -> list[SearchHit]:
    """Merge ranked lists; each hit scores sum(1 / (k + rank))."""
    scores: dict[int, float] = {}
    by_id: dict[int, SearchHit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.paragraph_id] = scores.get(hit.paragraph_id, 0.0) + 1.0 / (k + rank)
            by_id.setdefault(hit.paragraph_id, hit)
    ordered = sorted(scores, key=scores.__getitem__, reverse=True)
    return [by_id[pid].model_copy(update={"score": scores[pid]}) for pid in ordered]


class HybridRetriever:
    def __init__(self, retrievers: Sequence[Retriever]) -> None:
        self._retrievers = retrievers

    def retrieve(self, query: ParsedQuery, filters: SearchFilters, limit: int) -> list[SearchHit]:
        return reciprocal_rank_fusion([r.retrieve(query, filters, limit) for r in self._retrievers])[:limit]


def best_per_judgment(hits: list[SearchHit]) -> list[SearchHit]:
    """Keep the first (best) paragraph of each judgment, preserving order."""
    seen: set[str] = set()
    best = []
    for hit in hits:
        if hit.judgment_id not in seen:
            seen.add(hit.judgment_id)
            best.append(hit)
    return best


class SearchService:
    """Fact-pattern, phrase and citation search. Retrieval strategy is chosen per call (for evals)."""

    def __init__(
        self,
        judgments: JudgmentRepository,
        citations: CitationRepository,
        retrievers: dict[SearchMode, Retriever],
        reranker: Reranker | None,
        *,
        rerank_depth: int,
        relevance_threshold: float,
        result_limit: int = 10,
        candidate_limit: int = 100,
    ) -> None:
        self._judgments = judgments
        self._citations = citations
        self._retrievers = retrievers
        self._reranker = reranker
        self._rerank_depth = rerank_depth
        self._threshold = relevance_threshold
        self._result_limit = result_limit
        self._candidate_limit = candidate_limit

    @property
    def default_mode(self) -> SearchMode:
        return SearchMode.HYBRID_RERANK if self._reranker else SearchMode.HYBRID

    def search(self, raw_query: str, filters: SearchFilters, mode: SearchMode | None = None) -> SearchResponse:
        if is_citation_query(raw_query):
            return self._by_citation(raw_query)
        query = parse_query(raw_query)
        if query.is_empty:
            raise InvalidRequestError("Add at least one word or phrase to search for (NOT only excludes).")
        hits = self.rank(query, filters, mode or self.default_mode)
        results = self._hydrate(hits)
        return SearchResponse(query_type="fact_pattern", results=results, message=None if results else NO_RESULTS)

    def rank(
        self,
        query: ParsedQuery,
        filters: SearchFilters,
        mode: SearchMode,
        per_judgment: bool = True,
        relevance_cutoff: bool = True,
    ) -> list[SearchHit]:
        """Ranked paragraph hits after optional reranking and thresholding.

        per_judgment keeps only the best paragraph of each judgment (search results); turn it off to rank
        paragraphs inside one judgment (follow-up questions). relevance_cutoff drops weak matches; inside one
        judgment it is turned off, because general questions ("what was decided?") match no paragraph closely.
        """
        rerank = mode == SearchMode.HYBRID_RERANK
        if rerank and not self._reranker:
            raise ValueError("reranking is disabled in this deployment")
        retriever = self._retrievers[SearchMode.HYBRID if rerank else mode]
        candidates = retriever.retrieve(query, filters, self._candidate_limit)
        if per_judgment:
            candidates = best_per_judgment(candidates)
        if not rerank:
            return candidates[: self._result_limit]
        reranked = self._rerank(query, candidates[: self._rerank_depth], relevance_cutoff)
        return reranked[: self._result_limit]

    def _rerank(self, query: ParsedQuery, candidates: list[SearchHit], relevance_cutoff: bool) -> list[SearchHit]:
        paragraphs = self._judgments.paragraphs_by_ids(h.paragraph_id for h in candidates)
        candidates = [h for h in candidates if h.paragraph_id in paragraphs]
        texts = [paragraphs[h.paragraph_id][1].text for h in candidates]
        scores = self._reranker.score(query.rerank_text, texts)
        rescored = [h.model_copy(update={"score": s}) for h, s in zip(candidates, scores, strict=True)]
        if relevance_cutoff:
            rescored = [h for h in rescored if h.score >= self._threshold]
        return sorted(rescored, key=lambda h: h.score, reverse=True)

    def _hydrate(self, hits: list[SearchHit]) -> list[SearchResult]:
        paragraphs = self._judgments.paragraphs_by_ids(h.paragraph_id for h in hits)
        summaries = self._judgments.summaries(h.judgment_id for h in hits)
        return [
            SearchResult(
                judgment=summaries[h.judgment_id],
                matched_paragraph=paragraphs[h.paragraph_id][1],
                score=round(h.score, 4),
            )
            for h in hits
            if h.paragraph_id in paragraphs and h.judgment_id in summaries
        ]

    def _by_citation(self, raw_query: str) -> SearchResponse:
        norm = normalize_citation(raw_query)
        judgment_id = self._citations.resolve(norm) if norm else None
        if not judgment_id:
            return SearchResponse(query_type="citation", results=[], message=NOT_IN_CORPUS)
        judgment = self._judgments.summaries([judgment_id])[judgment_id]
        first = self._judgments.paragraphs(judgment_id)[:1]
        results = [SearchResult(judgment=judgment, matched_paragraph=first[0], score=1.0)] if first else []
        return SearchResponse(query_type="citation", results=results)
