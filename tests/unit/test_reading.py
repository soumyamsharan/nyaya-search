import pytest

from nyaya.domain import Paragraph, SearchHit, SearchMode
from nyaya.errors import LlmBusyError, LlmUnavailableError, NotFoundError
from nyaya.grounding import GroundingFilter
from nyaya.llm import GuardedLlm
from nyaya.reading import (
    NO_SUPPORTED_ANSWER,
    NOT_ADDRESSED,
    BreakdownService,
    QuestionService,
    select_breakdown_paragraphs,
)
from nyaya.search import SearchService
from tests.fakes import (
    FakeBreakdownCache,
    FakeCallLog,
    FakeChatClient,
    FakeCitations,
    FakeJudgments,
    OverlapReranker,
    StaticRetriever,
)

PARAS = [Paragraph(seq=i, label=str(i), text=f"paragraph {i} about the demand notice service") for i in range(1, 31)]
SUPPORTED = {"text": "paragraph 2 about the demand notice service", "paras": [2]}


def test_breakdown_context_prioritises_headnote_paragraphs_within_budget():
    chosen = select_breakdown_paragraphs(PARAS, headnote_labels=[17], token_budget=60)
    seqs = [p.seq for p in chosen]
    assert 17 in seqs
    assert seqs == sorted(seqs)
    assert len(seqs) < len(PARAS)


def breakdown_service(content=None, error=None, cache=None, today=0):
    chat = FakeChatClient(content, error)
    svc = BreakdownService(
        FakeJudgments({"J1": PARAS}, front={"J1": {"headnotes": "Held [Para 2]"}}),
        cache or FakeBreakdownCache(),
        GuardedLlm(chat, FakeCallLog(today), daily_cap=5),
        GroundingFilter(OverlapReranker(), 0.5),
        token_budget=2000,
    )
    return svc, chat


def test_breakdown_is_generated_grounded_and_cached():
    cache = FakeBreakdownCache()
    svc, chat = breakdown_service({"facts": [SUPPORTED], "held": [{"text": "made up", "paras": []}]}, cache=cache)
    breakdown = svc.get("J1")
    assert [s.text for s in breakdown.facts] == [SUPPORTED["text"]]
    assert breakdown.held == []
    again, _ = breakdown_service(error=LlmBusyError("capped"), cache=cache)
    assert again.get("J1") == breakdown  # served from cache without calling the model
    assert len(chat.calls) == 1


def test_breakdown_with_nothing_supported_is_unavailable_not_partial():
    svc, _ = breakdown_service({"facts": [{"text": "invented", "paras": [2]}]})
    with pytest.raises(LlmUnavailableError):
        svc.get("J1")


def test_breakdown_when_capped_and_not_cached_is_busy():
    svc, _ = breakdown_service({"facts": [SUPPORTED]}, today=5)
    with pytest.raises(LlmBusyError):
        svc.get("J1")


def test_breakdown_unknown_judgment():
    svc, _ = breakdown_service({})
    with pytest.raises(NotFoundError):
        svc.get("nope")


def question_service(content, hits=True):
    judgments = FakeJudgments({"J1": PARAS})
    retriever = StaticRetriever([SearchHit(paragraph_id=judgments.paragraph_id("J1", i), judgment_id="J1", score=1)
                                 for i in (1, 2, 3)] if hits else [])
    search = SearchService(judgments, FakeCitations(), {SearchMode.HYBRID: retriever}, OverlapReranker(),
                           rerank_depth=50, relevance_threshold=0.9)  # strict cut-off: must not apply here
    chat = FakeChatClient(content)
    llm = GuardedLlm(chat, FakeCallLog(), 5)
    svc = QuestionService(judgments, search, llm, GroundingFilter(OverlapReranker(), 0.5))
    return svc, chat, retriever


def test_question_answered_with_paragraph_citations_and_scoped_to_judgment():
    svc, _, retriever = question_service({"answerable": True, "sentences": [SUPPORTED]})
    answer = svc.ask("J1", "demand notice service")
    assert answer.answered and answer.sentences[0].paragraphs[0].label == "2"
    assert retriever.calls[0].judgment_id == "J1"


def test_question_not_addressed():
    svc, _, _ = question_service({"answerable": False, "sentences": []})
    answer = svc.ask("J1", "demand notice service")
    assert not answer.answered and answer.message == NOT_ADDRESSED


def test_general_question_still_reaches_the_model_with_opening_and_closing_paragraphs():
    svc, chat, _ = question_service({"answerable": False, "sentences": []})
    svc.ask("J1", "What was the main legal issue before the court?")  # matches no paragraph closely
    sent = chat.calls[0][1]
    for seq in (1, 2, 3, 29, 30):  # ranked candidates despite low scores, plus opening and closing paragraphs
        assert f"[P{seq}]" in sent
    assert sent.index("[P1]") < sent.index("[P29]")  # document order


def test_question_with_no_retrieved_paragraphs_still_uses_opening_and_closing():
    svc, chat, _ = question_service({"answerable": False, "sentences": []}, hits=False)
    assert svc.ask("J1", "anything").message == NOT_ADDRESSED
    assert "[P1]" in chat.calls[0][1] and "[P30]" in chat.calls[0][1]


def test_answer_with_every_sentence_dropped_says_no_supported_answer():
    svc, _, _ = question_service({"answerable": True, "sentences": [{"text": "invented claim", "paras": [2]}]})
    answer = svc.ask("J1", "demand notice service")
    assert not answer.answered and answer.message == NO_SUPPORTED_ANSWER
