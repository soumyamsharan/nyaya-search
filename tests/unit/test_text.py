import pytest

from nyaya.text import (
    extract_citations,
    find_case_names,
    find_section_references,
    has_overruling_language,
    headnote_paragraph_refs,
    is_citation_query,
    normalize_act,
    normalize_citation,
    parse_query,
)


@pytest.mark.parametrize(
    ("text", "norm"),
    [
        ("(2007) 3 SCC 755", "SCC|2007|3||755"),
        ("(1994) Supp.1 SCC 74", "SCC|1994||S1|74"),
        ("[2024] 10 S.C.R. 108", "SCR|2024|10||108"),
        ("[2001] 4 Supp. SCR 263", "SCR|2001|4|S|263"),
        ("AIR 1973 SC 1461", "AIR|1973|||1461"),
        ("2024 INSC 735", "INSC|2024|||735"),
        ("2023 SCC OnLine SC 1234", "SCCOL|2023|||1234"),
    ],
)
def test_citation_formats_normalise(text, norm):
    assert normalize_citation(text) == norm


def test_spacing_and_dots_do_not_change_the_key():
    assert normalize_citation("[2024]10 SCR 108") == normalize_citation("[2024] 10 S.C.R. 108")


def test_parallel_citations_found_in_order():
    found = extract_citations("State of Goa v. Sanjay Thakran [2007] 3 SCR 507 : (2007) 3 SCC 755; other text")
    assert [c.norm for c in found] == ["SCR|2007|3||507", "SCC|2007|3||755"]


def test_scc_online_is_not_read_as_plain_scc():
    assert [c.norm.split("|")[0] for c in extract_citations("(2023) SCC OnLine SC 99 and 2023 SCC OnLine SC 99")] \
        == ["SCCOL"]


def test_citation_query_detection():
    assert is_citation_query(" (2019) 5 SCC 123 ")
    assert is_citation_query("2024 INSC 512.")
    assert not is_citation_query("eviction (2019) 5 SCC 123")
    assert not is_citation_query("tenant default eviction")


def test_quoted_phrases_are_split_from_free_text():
    parsed = parse_query('"no longer good law" eviction of tenant')
    assert parsed.phrases == ["no longer good law"]
    assert parsed.free_text == "eviction of tenant"
    assert parse_query('   ').is_empty


def test_act_names_normalise_for_matching():
    assert normalize_act("The Negotiable Instruments Act, 1881.") == "negotiable instruments act 1881"


def test_section_references():
    refs = find_section_references("a complaint under Section 138 of the Negotiable Instruments Act, 1881 was filed")
    assert refs == [("Negotiable Instruments Act, 1881", "138")]


def test_headnote_paragraph_refs_expand_ranges():
    assert headnote_paragraph_refs("Held ... [Para 27] and [Paras 21-23, 30]") == [27, 21, 22, 23, 30]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The decision in X stands overruled.", True),
        ("X is no longer good law.", True),
        ("We overrule the view taken in X.", True),
        ("We follow the view taken in X.", False),
    ],
)
def test_overruling_language(text, expected):
    assert has_overruling_language(text) is expected


def test_case_names():
    assert find_case_names("as held in State of Goa v. Sanjay Thakran, the court") == ["State of Goa v. Sanjay Thakran"]


@pytest.mark.parametrize(
    ("query", "free", "required", "excluded"),
    [
        ("cheque AND dishonour", "cheque dishonour", ["cheque", "dishonour"], []),
        ("bail NOT anticipatory", "bail", [], ["anticipatory"]),
        ('eviction NOT "bona fide requirement"', "eviction", [], ["bona fide requirement"]),
        ("notice not received", "notice not received", [], []),
        ("eviction OR ejectment", "eviction ejectment", [], []),
        ('a AND b AND "c d" NOT e', "a b", ["a", "b", "c d"], ["e"]),
    ],
)
def test_boolean_operators(query, free, required, excluded):
    parsed = parse_query(query)
    assert (parsed.free_text, parsed.required, parsed.excluded) == (free, required, excluded)


def test_only_excluded_terms_is_empty():
    assert parse_query("NOT bail").is_empty
