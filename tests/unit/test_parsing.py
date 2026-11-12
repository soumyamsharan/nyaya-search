from pathlib import Path

from nyaya.parsing.pdf import Line, extract_pdf
from nyaya.parsing.scr import parse_bench, parse_judgment

FIXTURE = Path(__file__).parents[1] / "fixtures" / "2024_10_108_125_EN.pdf"
HEADER = ["[2024] 10 S.C.R. 108 : 2024 INSC 735", "A v. B", "[Bela Trivedi and Satish Sharma,* JJ.]"]


def lines(*texts: str, block_per_line: bool = False) -> list[Line]:
    return [Line(t, i if block_per_line else 0) for i, t in enumerate(texts)]


def body(*texts: str) -> list[Line]:
    return lines(*HEADER, "Headnotes", "Held: something [Para 2]", "Judgment / Order of the Supreme Court",
                 "Judgment", "Satish Sharma, J.", *texts)


def test_numbered_paragraphs_keep_printed_numbers():
    parsed = parse_judgment(body("1. First.", "continues", "2. Second.", "3. Third."))
    assert [p.label for p in parsed.paragraphs] == ["1", "2", "3"]
    assert parsed.paragraphs[0].text == "First. continues"
    assert not any(p.label_derived for p in parsed.paragraphs)


def test_restarted_numbering_in_a_separate_opinion_gets_unique_labels():
    parsed = parse_judgment(body("1. A.", "2. B.", "3. C.", "Bela Trivedi, J.", "1. D.", "2. E."))
    assert [p.label for p in parsed.paragraphs] == ["1", "2", "3", "O2-1", "O2-2"]
    assert len({p.seq for p in parsed.paragraphs}) == 5


def test_numbered_clauses_inside_a_quotation_stay_in_their_paragraph():
    parsed = parse_judgment(body("1. A.", "2. The rule reads:", "1. clause one", "2. clause two", "3. C."))
    assert [p.label for p in parsed.paragraphs] == ["1", "2", "3"]
    assert "clause one" in parsed.paragraphs[1].text


def test_unnumbered_paragraph_one_before_two():
    parsed = parse_judgment(body("Leave granted.", "2. Facts follow.", "3. More."))
    assert [(p.label, p.text) for p in parsed.paragraphs][:2] == [("1", "Leave granted."), ("2", "Facts follow.")]


def test_unnumbered_order_gets_derived_labels():
    text = "This is an unnumbered order paragraph that is long enough to stand on its own as a paragraph here."
    parsed = parse_judgment(
        [*lines(*HEADER), Line("Judgment / Order of the Supreme Court", 0), Line(text, 1), Line(text, 2)]
    )
    assert [p.label for p in parsed.paragraphs] == ["1", "2"]
    assert all(p.label_derived for p in parsed.paragraphs)


def test_front_matter_is_kept_separate_from_paragraphs():
    parsed = parse_judgment(body("1. First.", "2. Second."))
    assert parsed.front_matter["headnotes"] == "Held: something [Para 2]"
    assert all("Held:" not in p.text for p in parsed.paragraphs)


def test_result_line_ends_the_body():
    parsed = parse_judgment(body("1. A.", "2. B.", "Result of the Case: Appeal allowed."))
    assert parsed.front_matter["result"] == "Appeal allowed."
    assert "Result" not in parsed.paragraphs[-1].text


def test_bench_and_author():
    assert parse_bench("[Bela M. Trivedi and Satish Chandra Sharma,* JJ.]") == (
        ["Bela M. Trivedi", "Satish Chandra Sharma"], "Satish Chandra Sharma")
    assert parse_bench("[Dr Dhananjaya Y Chandrachud,* CJI, J.B. Pardiwala and Manoj Misra, JJ.]") == (
        ["Dr Dhananjaya Y Chandrachud", "J.B. Pardiwala", "Manoj Misra"], "Dr Dhananjaya Y Chandrachud")


def test_real_pdf_paragraphs_front_matter_and_page_furniture():
    text = extract_pdf(FIXTURE.read_bytes())
    parsed = parse_judgment(text.lines)
    labels = [p.label for p in parsed.paragraphs]
    assert labels == [str(n) for n in range(1, 39)]
    assert parsed.author == "Satish Chandra Sharma"
    assert {"headnotes", "case_law_cited", "acts", "issue"} <= parsed.front_matter.keys()
    joined = " ".join(p.text for p in parsed.paragraphs)
    assert "S.C.R." not in joined  # running header dropped
    assert "Digital Supreme Court Reports" not in joined
    assert "Headnotes prepared by" not in joined  # footnote dropped
    assert "Trial Court1" not in joined  # superscript footnote marker dropped
    assert not text.looks_scanned


def test_re_parsing_is_deterministic():
    data = FIXTURE.read_bytes()
    first = parse_judgment(extract_pdf(data).lines).paragraphs
    second = parse_judgment(extract_pdf(data).lines).paragraphs
    assert first == second


def test_blank_pdf_looks_scanned():
    import pymupdf

    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    assert extract_pdf(doc.tobytes()).looks_scanned


def test_quoted_judgment_with_its_own_numbering_stays_inside_the_quoting_paragraph():
    parsed = parse_judgment(body(
        "1. A.", "2. B.", "3. The High Court held:", "3. Quoted three.", "4. Quoted four.", "5. Quoted five.",
        "4. Real four.", "5. Real five.",
    ))
    assert [p.label for p in parsed.paragraphs] == ["1", "2", "3", "4", "5"]
    assert "Quoted five" in parsed.paragraphs[2].text
    assert parsed.paragraphs[3].text == "Real four."


def test_quoted_statute_section_does_not_swallow_the_next_paragraph():
    parsed = parse_judgment(body("1. A.", "2. B.", "3. Rule reads:", "2. Quoted rule text.", "4. Real four."))
    assert [p.label for p in parsed.paragraphs] == ["1", "2", "3", "4"]
