from nyaya.statute_refs import CONSTITUTION_KEY, find_all_statute_refs


def by_kind(text):
    return {(m.kind, m.key, m.slug) for m in find_all_statute_refs(text)}


def test_constitution_articles_including_lists():
    assert by_kind("Article 21 of the Constitution guarantees life.") == {("article", CONSTITUTION_KEY, "21")}
    got = by_kind("Articles 14 and 21 of the Constitution were relied on.")
    assert {("article", CONSTITUTION_KEY, "14"), ("article", CONSTITUTION_KEY, "21")} == got


def test_article_numbers_match_exactly():
    assert by_kind("Article 210 of the Constitution") == {("article", CONSTITUTION_KEY, "210")}


def test_rules_are_under_their_parent_act():
    got = find_all_statute_refs("Order XII Rule 6 of the Code of Civil Procedure, 1908 allows judgment on admission.")
    assert [(m.kind, m.key, m.number, m.slug) for m in got] == [
        ("rule", "code-of-civil-procedure", "Order XII Rule 6", "xii-6")
    ]


def test_rules_without_a_stated_parent_are_not_guessed():
    assert find_all_statute_refs("The Rule 6 requires notice.") == []


def test_regulations_under_their_parent():
    got = find_all_statute_refs("Regulation 12 of the Regulations, 2014 applies.")
    assert got == [] or all(m.kind == "regulation" for m in got)
    got2 = find_all_statute_refs("Regulation 12 of the Telecom Regulatory Authority of India Act, 1997 applies.")
    expected = ("regulation", "telecom-regulatory-authority-of-india-act", "12")
    assert [(m.kind, m.key, m.slug) for m in got2] == [expected]


def test_notifications_and_ordinances():
    text = "Notification No. 45/2019 was issued; Ordinance 12 of 2020."
    got = {(m.kind, m.slug) for m in find_all_statute_refs(text)}
    assert ("notification", "45-2019") in got and ("notification", "12-2020") in got


def test_section_references_still_found():
    got = by_kind("Section 138 of the Negotiable Instruments Act, 1881 was filed.")
    assert ("section", "negotiable-instruments-act", "138") in got
