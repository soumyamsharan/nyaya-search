import pytest

from nyaya.domain import Outcome, Paragraph, Role, SearchFilters, SearchHit, SearchMode
from nyaya.errors import InvalidRequestError
from nyaya.search import (
    NO_RESULTS,
    NOT_IN_CORPUS,
    OUTCOME_VALUES,
    SearchService,
    best_per_judgment,
    filter_sql,
    reciprocal_rank_fusion,
    term_pattern,
    term_sql,
)
from nyaya.text import normalize_citation, parse_query
from tests.fakes import FakeCitations, FakeJudgments, OverlapReranker, StaticRetriever


def hit(pid: int, jid: str, score: float = 1.0) -> SearchHit:
    return SearchHit(paragraph_id=pid, judgment_id=jid, score=score)


def test_rrf_rewards_agreement_between_rankings():
    fused = reciprocal_rank_fusion([[hit(1, "A"), hit(2, "B")], [hit(2, "B"), hit(3, "C")]])
    assert [h.paragraph_id for h in fused] == [2, 1, 3]


def test_best_paragraph_per_judgment_keeps_order():
    assert [h.paragraph_id for h in best_per_judgment([hit(1, "A"), hit(2, "A"), hit(3, "B")])] == [1, 3]


def test_filters_are_parameterised_not_interpolated():
    where, params = filter_sql(SearchFilters(judge="x'; DROP TABLE judgments; --", act="NI Act", section="138"))
    assert "DROP" not in where
    assert params["judge0"] == "%x'; DROP TABLE judgments; --%"
    assert params["section"] == "138"


@pytest.fixture
def judgments() -> FakeJudgments:
    return FakeJudgments(
        {
            "J1": [Paragraph(seq=1, label="1", text="demand notice under section 138 was never received")],
            "J2": [Paragraph(seq=1, label="1", text="landlord tenant eviction for arrears of rent")],
        }
    )


RERANKER = OverlapReranker()


def service(judgments, hits, reranker=RERANKER, threshold=0.3, aliases=None) -> SearchService:
    retriever = StaticRetriever(hits)
    return SearchService(
        judgments,
        FakeCitations(aliases),
        {SearchMode.BM25: retriever, SearchMode.VECTOR: retriever, SearchMode.HYBRID: retriever},
        reranker,
        rerank_depth=50,
        relevance_threshold=threshold,
    )


def test_fact_pattern_search_reranks_and_returns_matched_paragraph(judgments):
    hits = [hit(judgments.paragraph_id("J2", 1), "J2"), hit(judgments.paragraph_id("J1", 1), "J1")]
    response = service(judgments, hits).search("demand notice never received", SearchFilters())
    assert response.query_type == "fact_pattern"
    assert [r.judgment.id for r in response.results] == ["J1"]  # J2 falls below the relevance threshold
    assert response.results[0].matched_paragraph.label == "1"


def test_no_relevant_results_gives_a_message(judgments):
    hits = [hit(judgments.paragraph_id("J2", 1), "J2")]
    response = service(judgments, hits).search("patent infringement", SearchFilters())
    assert response.results == []
    assert response.message == NO_RESULTS


def test_citation_query_returns_only_that_judgment(judgments):
    svc = service(judgments, [], aliases={normalize_citation("2024 INSC 735"): "J1"})
    response = svc.search("2024 INSC 735", SearchFilters())
    assert response.query_type == "citation"
    assert [r.judgment.id for r in response.results] == ["J1"]


def test_citation_not_in_corpus_says_so(judgments):
    response = service(judgments, [hit(1, "J1")]).search("(2019) 5 SCC 123", SearchFilters())
    assert response.results == []
    assert response.message == NOT_IN_CORPUS


def test_without_reranker_default_mode_is_hybrid(judgments):
    svc = service(judgments, [hit(judgments.paragraph_id("J1", 1), "J1")], reranker=None)
    assert svc.default_mode == SearchMode.HYBRID
    assert [r.judgment.id for r in svc.search("anything", SearchFilters()).results] == ["J1"]


def test_paragraph_ranking_within_one_judgment_keeps_all_paragraphs():
    judgments = FakeJudgments({"J1": [Paragraph(seq=i, label=str(i), text=f"notice text {i}") for i in (1, 2, 3)]})
    hits = [hit(judgments.paragraph_id("J1", i), "J1") for i in (1, 2, 3)]
    svc = service(judgments, hits, threshold=0.0)
    filters = SearchFilters(judgment_id="J1")
    ranked = svc.rank(parse_query("notice"), filters, SearchMode.HYBRID_RERANK, per_judgment=False)
    assert len(ranked) == 3


def test_new_filters_compile_to_parameters():
    where, params = filter_sql(SearchFilters(
        judges=["Pardiwala", "Mahadevan"], author="Oka", outcome=Outcome.DISMISSED,
        roles=[Role.REASONING, Role.CONCLUSION], date_from="2025-01-01", date_to="2025-03-31"))
    assert params["judge0"] == "%Pardiwala%" and params["judge1"] == "%Mahadevan%"
    assert params["author"] == "%Oka%"
    assert params["outcome"] == OUTCOME_VALUES[Outcome.DISMISSED]
    assert params["roles"] == ["reasoning", "conclusion"]
    assert "p.role = ANY" in where and "j.decision_date <= %(date_to)s" in where


def test_other_outcome_means_none_of_the_known_values():
    where, params = filter_sql(SearchFilters(outcome=Outcome.OTHER))
    assert "IS NULL OR NOT" in where and "Dismissed" in params["known_outcomes"]


def test_term_conditions_for_and_not():
    sql, params = term_sql(parse_query('cheque AND dishonour NOT "bona fide requirement"'))
    assert sql.count("~*") == 3 and sql.count("!~*") == 1
    assert params["exc0"] == r"\mbona\s+fide\s+requirement\M"


def test_term_pattern_escapes_and_handles_punctuation():
    assert term_pattern("s.138") == r"\ms\.138\M"
    assert term_pattern("(a)") == r"\(a\)"


def test_only_excluded_terms_is_rejected(judgments):
    with pytest.raises(InvalidRequestError):
        service(judgments, []).search("NOT bail", SearchFilters())
