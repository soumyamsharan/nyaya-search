"""Composition root: builds every service from settings, once. Callers depend on the services, not on how
they are wired."""

from dataclasses import dataclass

from nyaya.config import Settings
from nyaya.db import Database
from nyaya.domain import SearchMode
from nyaya.grounding import GroundingFilter
from nyaya.llm import GuardedLlm, OpenAICompatibleClient
from nyaya.ml import Reranker, build_embedder, build_reranker
from nyaya.notes import NoteRepository
from nyaya.reading import BreakdownService, QuestionService
from nyaya.repos import BreakdownCache, CitationRepository, JudgmentRepository, LlmCallLog, StatuteRepository
from nyaya.search import Bm25Retriever, HybridRetriever, SearchService, VectorRetriever
from nyaya.spelling import SpellingCorrector


@dataclass
class Services:
    db: Database
    judgments: JudgmentRepository
    citations: CitationRepository
    statutes: StatuteRepository
    notes: NoteRepository
    search: SearchService
    breakdowns: BreakdownService
    questions: QuestionService

    def close(self) -> None:
        self.db.close()


def build_services(settings: Settings, reranker: Reranker | None = None) -> Services:
    db = Database(settings.database_dsn)
    judgments = JudgmentRepository(db)
    citations = CitationRepository(db, judgments)
    statutes = StatuteRepository(db, judgments)
    embedder = build_embedder(settings)
    reranker = reranker or build_reranker(settings)

    bm25 = Bm25Retriever(db)
    vector = VectorRetriever(db, embedder)
    search = SearchService(
        judgments,
        citations,
        {SearchMode.BM25: bm25, SearchMode.VECTOR: vector, SearchMode.HYBRID: HybridRetriever([bm25, vector])},
        reranker,
        rerank_depth=settings.rerank_depth,
        relevance_threshold=settings.relevance_threshold,
        result_limit=settings.result_limit,
        candidate_limit=settings.candidate_limit,
        spelling=SpellingCorrector(db),
    )

    llm = GuardedLlm(
        OpenAICompatibleClient(
            settings.llm_base_url, settings.llm_model, settings.llm_api_key, settings.llm_timeout_seconds
        ),
        LlmCallLog(db),
        settings.llm_daily_cap,
    )
    if reranker is None:
        raise ValueError("grounding needs a reranker model; set RERANK_DEPTH > 0")
    grounding = GroundingFilter(reranker, settings.support_threshold)
    return Services(
        db=db,
        judgments=judgments,
        citations=citations,
        statutes=statutes,
        notes=NoteRepository(db),
        search=search,
        breakdowns=BreakdownService(judgments, BreakdownCache(db), llm, grounding, settings.llm_context_tokens),
        questions=QuestionService(judgments, search, llm, grounding),
    )
