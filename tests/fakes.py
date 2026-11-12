"""Test doubles shared by unit tests. They implement the same small interfaces as the real classes."""

import re
from dataclasses import dataclass, field

from nyaya.domain import (
    Answer,
    Breakdown,
    CitationGraph,
    Judgment,
    JudgmentSummary,
    Paragraph,
    SearchFilters,
    SearchHit,
    SearchResponse,
)
from nyaya.errors import NotFoundError
from nyaya.llm import LlmResult


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class OverlapReranker:
    """Score = share of the query's words found in the document (0..1)."""

    def score(self, query: str, documents: list[str]) -> list[float]:
        q = words(query)
        return [len(q & words(d)) / len(q) if q else 0.0 for d in documents]


class StaticRetriever:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls: list[SearchFilters] = []

    def retrieve(self, query, filters, limit):
        self.calls.append(filters)
        return self.hits[:limit]


def summary(judgment_id: str = "J1", title: str = "A v. B") -> JudgmentSummary:
    return JudgmentSummary(id=judgment_id, title=title, decision_date=None, bench=["X"], citation="2024 INSC 1")


@dataclass
class FakeJudgments:
    paragraphs_by_judgment: dict[str, list[Paragraph]] = field(default_factory=dict)
    front: dict[str, dict[str, str]] = field(default_factory=dict)

    def _ids(self) -> dict[int, tuple[str, Paragraph]]:
        # paragraph id = judgment index * 1000 + seq
        out = {}
        for j_index, (jid, paras) in enumerate(sorted(self.paragraphs_by_judgment.items())):
            for p in paras:
                out[j_index * 1000 + p.seq] = (jid, p)
        return out

    def paragraph_id(self, judgment_id: str, seq: int) -> int:
        return next(pid for pid, (jid, p) in self._ids().items() if jid == judgment_id and p.seq == seq)

    def summaries(self, ids):
        return {i: summary(i) for i in ids if i in self.paragraphs_by_judgment}

    def paragraphs_by_ids(self, ids):
        all_ids = self._ids()
        return {i: all_ids[i] for i in ids if i in all_ids}

    def paragraphs(self, judgment_id):
        return self.paragraphs_by_judgment.get(judgment_id, [])

    def front_matter(self, judgment_id):
        return self.front.get(judgment_id, {})

    def exists(self, judgment_id):
        return judgment_id in self.paragraphs_by_judgment


class FakeCitations:
    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self.aliases = aliases or {}

    def resolve(self, norm):
        return self.aliases.get(norm)


class FakeChatClient:
    model = "fake-model"

    def __init__(self, content: dict | None = None, error: Exception | None = None) -> None:
        self.content = content or {}
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> LlmResult:
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return LlmResult(self.content, 100, 20)


class FakeCallLog:
    def __init__(self, today: int = 0) -> None:
        self.today = today
        self.rows: list[dict] = []

    def calls_today(self) -> int:
        return self.today

    def record(self, **fields):
        self.rows.append(fields)


class FakeBreakdownCache:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def latest(self, judgment_id, prompt_version):
        return self.store.get(judgment_id)

    def put(self, judgment_id, prompt_version, model, content):
        self.store[judgment_id] = content


# --- API-level fakes ---------------------------------------------------------------------------------


class FakeDb:
    def fetch_one(self, sql, params=None):
        return {"ok": 1}

    def close(self):
        pass


@dataclass
class FakeServices:
    """Stands in for nyaya.container.Services in API tests."""

    search_response: SearchResponse | None = None
    judgment: Judgment | None = None
    breakdown_error: Exception | None = None
    answer: Answer | None = None
    db: FakeDb = field(default_factory=FakeDb)

    def __post_init__(self) -> None:
        outer = self

        class _Search:
            def search(self, q, filters, mode):
                outer.last_search = (q, filters, mode)
                return outer.search_response or SearchResponse(query_type="fact_pattern", results=[])

        class _Judgments:
            def get(self, judgment_id):
                return outer.judgment if outer.judgment and outer.judgment.id == judgment_id else None

            def exists(self, judgment_id):
                return self.get(judgment_id) is not None

        class _Breakdowns:
            def get(self, judgment_id):
                if outer.breakdown_error:
                    raise outer.breakdown_error
                if not outer.judgment or outer.judgment.id != judgment_id:
                    raise NotFoundError("judgment not found")
                return Breakdown(facts=[], issues=[], held=[], ratio=[], model="fake")

        class _Questions:
            def ask(self, judgment_id, question):
                outer.last_question = question
                return outer.answer or Answer(answered=False, sentences=[], message="not addressed")

        class _Citations:
            def graph(self, judgment_id):
                return CitationGraph(cites=[], cited_by=[], unresolved=[], overruling_evidence=[])

        self.search = _Search()
        self.judgments = _Judgments()
        self.breakdowns = _Breakdowns()
        self.questions = _Questions()
        self.citations = _Citations()

    def close(self) -> None:
        pass


def judgment(judgment_id: str = "2024_10_108_125") -> Judgment:
    return Judgment(
        **summary(judgment_id).model_dump(),
        author="X",
        neutral_citation="2024 INSC 1",
        scr_citation=None,
        disposal_nature=None,
        pdf_url="https://example.invalid/a.pdf",
        acts=[],
        reporter_front_matter=[],
        paragraphs=[Paragraph(seq=1, label="1", text="Text.")],
        numbering_derived=False,
    )
