from nyaya.domain import Paragraph
from nyaya.grounding import GeneratedSentence, GroundingFilter, parse_sentences
from tests.fakes import OverlapReranker

CONTEXT = {
    3: Paragraph(seq=3, label="3", text="The demand notice was sent to the correct address but returned unclaimed."),
    7: Paragraph(seq=7, label="7", text="Following State of Goa v. Sanjay Thakran (2007) 3 SCC 755, the appeal is "
                                        "allowed and the acquittal restored."),
}


def grounded(*sentences: GeneratedSentence):
    return GroundingFilter(OverlapReranker(), support_threshold=0.5).apply(list(sentences), CONTEXT)


def test_supported_sentence_is_kept_with_its_paragraph_labels():
    kept, dropped = grounded(GeneratedSentence("The demand notice was returned unclaimed.", [3]))
    assert dropped == 0
    assert kept[0].paragraphs[0].label == "3"


def test_uncited_sentence_is_dropped():
    assert grounded(GeneratedSentence("The demand notice was returned unclaimed.", [])) == ([], 1)


def test_sentence_citing_a_paragraph_not_supplied_is_dropped():
    assert grounded(GeneratedSentence("The demand notice was returned unclaimed.", [3, 99])) == ([], 1)


def test_invented_citation_is_dropped():
    sentence = GeneratedSentence("The appeal is allowed following (2015) 2 SCC 100.", [7])
    assert grounded(sentence) == ([], 1)


def test_citation_present_in_context_is_allowed():
    kept, _ = grounded(GeneratedSentence("Following (2007) 3 SCC 755, the appeal is allowed.", [7]))
    assert len(kept) == 1


def test_invented_case_name_is_dropped():
    sentence = GeneratedSentence("Following Ramesh Kumar v. State of Punjab, the appeal is allowed.", [7])
    assert grounded(sentence) == ([], 1)


def test_unsupported_claim_is_dropped():
    assert grounded(GeneratedSentence("The tenant must vacate within six months.", [3])) == ([], 1)


def test_parse_sentences_tolerates_messy_model_output():
    parsed = parse_sentences([
        {"text": "Held that notice was served [P3].", "paras": ["P3", 3]},
        {"text": "", "paras": [1]},
        "not a dict",
        {"text": "Ratio stated.", "paras": "7"},
    ])
    assert parsed == [
        GeneratedSentence("Held that notice was served.", [3, 3]),
        GeneratedSentence("Ratio stated.", [7]),
    ]
    assert parse_sentences("nope") == []
