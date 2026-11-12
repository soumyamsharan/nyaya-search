from nyaya.domain import Paragraph, SearchFilters, SearchHit, SearchMode
from nyaya.search import SearchService, filter_sql, name_match
from nyaya.spelling import apply_corrections, candidate_words
from tests.fakes import FakeCitations, FakeJudgments, OverlapReranker, StaticRetriever


def test_corrections_keep_operators_quotes_and_case():
    raw = '"Demand notise" AND tennant NOT arears'
    fixed = apply_corrections(raw, {"notise": "notice", "tennant": "tenant", "arears": "arrears"})
    assert fixed == '"Demand notice" AND tenant NOT arrears'


def test_only_long_non_operator_words_are_checked():
    assert candidate_words("bail AND the NOT anticipatery of") == ["bail", "anticipatery"]


def test_short_names_match_exactly_long_names_fuzzily():
    assert "word_similarity" not in name_match("j.author", "author", "Oka")
    assert "word_similarity" in name_match("j.author", "author", "Pardivala")
    where, params = filter_sql(SearchFilters(judges=["Pardivala"]))
    assert params["judge0_raw"] == "Pardivala" and "word_similarity" in where


class FakeSpelling:
    def unknown_words(self, raw):
        return ["tennant"] if "tennant" in raw else []

    def suggest(self, raw, unknown=None):
        return raw.replace("tennant", "tenant")


def service(retriever):
    judgments = FakeJudgments({"J1": [Paragraph(seq=1, label="1", text="tenant eviction for arrears")]})
    retriever.hits = [SearchHit(paragraph_id=judgments.paragraph_id("J1", 1), judgment_id="J1", score=1)]
    return SearchService(judgments, FakeCitations(), {m: retriever for m in SearchMode}, OverlapReranker(),
                         rerank_depth=50, relevance_threshold=0.0, spelling=FakeSpelling())


class RecordingRetriever(StaticRetriever):
    def __init__(self):
        super().__init__([])
        self.queries = []

    def retrieve(self, query, filters, limit):
        self.queries.append(query)
        return super().retrieve(query, filters, limit)


def test_misspelled_query_gets_suggestion_and_fuzzy_keywords():
    retriever = RecordingRetriever()
    response = service(retriever).search("tennant eviction", SearchFilters())
    assert response.suggestion == "tenant eviction"
    assert retriever.queries[0].fuzzy is True


def test_correct_query_has_no_suggestion_and_exact_keywords():
    retriever = RecordingRetriever()
    response = service(retriever).search("tenant eviction", SearchFilters())
    assert response.suggestion is None
    assert retriever.queries[0].fuzzy is False


def test_citation_query_skips_spelling():
    retriever = RecordingRetriever()
    response = service(retriever).search("2024 INSC 874", SearchFilters())
    assert response.query_type == "citation" and response.suggestion is None and retriever.queries == []
