"""Parse a Digital SCR judgment (text lines) into bench, reporter front matter and numbered paragraphs."""

import re
from dataclasses import dataclass, field

from nyaya.parsing.pdf import Line

EXTRACTOR_VERSION = 3

BODY_MARKER = "judgment / order of the supreme court"
SECTION_LABELS = {
    "issue for consideration": "issue",
    "headnotes": "headnotes",
    "case law cited": "case_law_cited",
    "list of acts": "acts",
    "list of keywords": "keywords",
    "case arising from": "case_arising_from",
    "appearances for parties": "appearances",
}
SECTION_TITLES = {
    "issue": "Issue for consideration",
    "headnotes": "Headnotes",
    "case_law_cited": "Case law cited",
    "acts": "List of Acts",
    "keywords": "Keywords",
    "case_arising_from": "Case arising from",
    "appearances": "Appearances",
    "result": "Result of the case",
}

_PARA_START = re.compile(r"^(\d{1,3})\.\s*(.*)$")
_AUTHOR_LINE = re.compile(r"^(?:Dr\.?\s+)?[A-Z][A-Za-z.'\- ]{2,60},\s*(?:J|CJI|C\.J\.I)\.?$")
_HEADING_LINE = re.compile(r"^(?:J\s*U\s*D\s*G\s*M\s*E\s*N\s*T|O\s*R\s*D\s*E\s*R|Judgment|Order)\.?$", re.I)
_BENCH = re.compile(r"\[([^\[\]]*?\b(?:JJ?|CJI)\.?)\s*\]")
_RESULT = "result of the case:"
_STOP = ("headnotes prepared by",)
_MIN_DERIVED_CHARS = 80
_PARTY_LIST = re.compile(r"^R\d+\s*:", re.I)  # "R1: State of Uttar Pradesh" lists respondents, not the name
_VERSUS = re.compile(r"\s+(?:v\.?|vs\.?|versus)\s+", re.I)


@dataclass(frozen=True)
class ParsedParagraph:
    seq: int
    opinion_idx: int
    label: str
    label_derived: bool
    text: str


@dataclass
class ParsedJudgment:
    bench: list[str] = field(default_factory=list)
    author: str | None = None
    case_name: str | None = None
    front_matter: dict[str, str] = field(default_factory=dict)
    paragraphs: list[ParsedParagraph] = field(default_factory=list)


def join_lines(lines: list[str]) -> str:
    """Join wrapped lines, keeping hyphenated words together."""
    out = ""
    for line in lines:
        if out.endswith("-") and line[:1].islower():
            out += line
        else:
            out = f"{out} {line}" if out else line
    return out.strip()


def paragraph_label(opinion_idx: int, number: int) -> str:
    return str(number) if opinion_idx == 0 else f"O{opinion_idx + 1}-{number}"


def parse_bench(text: str) -> tuple[list[str], str | None]:
    """'[Bela M. Trivedi and Satish Chandra Sharma,* JJ.]' -> (names, author)."""
    match = _BENCH.search(text)
    if not match:
        return [], None
    inner = re.sub(r",?\s*\bJJ?\.?$", "", match.group(1).strip())
    names: list[str] = []
    author: str | None = None
    for token in re.split(r",|\band\b", inner):
        token = token.strip()
        starred = "*" in token
        token = token.replace("*", "").strip()
        if token.upper().rstrip(".") in {"", "CJI", "J"}:
            if starred and names:
                author = names[-1]
            continue
        names.append(token)
        if starred:
            author = token
    return names, author


def parse_case_name(header: list[str]) -> str | None:
    """The reporter's cause title from the header lines: 'Ashok Singh v. State of Uttar Pradesh & Anr.'.

    Header layout: citation line, the parties (split around "v."), optional "R1: ..." party lists, then the
    "(Criminal Appeal No. ...)" line. Returns None unless the result looks like "X v. Y".
    """
    parts: list[str] = []
    for line in header[1:] if header and header[0].startswith("[") else header:
        if line.startswith(("(", "[")):
            break
        if not _PARTY_LIST.match(line):
            parts.append(line)
    name = _VERSUS.sub(" v. ", f" {join_lines(parts)} ").strip()
    return name if " v. " in name and len(name) <= 300 else None


def _section_of(line: str) -> str | None:
    return SECTION_LABELS.get(line.rstrip("†* ").strip().lower())


def _split_front_and_body(lines: list[Line]) -> tuple[list[Line], list[Line]]:
    for i, line in enumerate(lines):
        if line.text.strip().lower() == BODY_MARKER:
            return lines[:i], lines[i + 1 :]
    return [], lines  # not Digital SCR: treat everything as body


def _parse_front_matter(lines: list[Line]) -> tuple[dict[str, str], list[str]]:
    sections: dict[str, list[str]] = {}
    header: list[str] = []
    current: str | None = None
    for line in lines:
        section = _section_of(line.text)
        if section:
            current = section
            sections.setdefault(section, [])
        elif current:
            sections[current].append(line.text)
        else:
            header.append(line.text)
    return {k: join_lines(v) for k, v in sections.items() if v}, header


def _numbered_paragraphs(lines: list[Line]) -> list[ParsedParagraph]:
    paragraphs: list[tuple[int, int, list[str]]] = []  # (opinion, number, lines)
    preamble: list[str] = []
    opinion = 0
    expected = 1
    new_opinion_pending = False
    for line in lines:
        text = line.text
        if _HEADING_LINE.match(text) or _AUTHOR_LINE.match(text):
            new_opinion_pending = bool(paragraphs)
            continue
        match = _PARA_START.match(text)
        number = int(match.group(1)) if match else None
        if number == 2 and not paragraphs and preamble:
            # Paragraph 1 is often printed without its number ("Leave granted." then "2."): the text before
            # "2." is paragraph 1.
            paragraphs.append((opinion, 1, preamble))
            preamble = []
            expected = 2
        if number is not None and number == expected:
            paragraphs.append((opinion, number, [match.group(2)] if match.group(2) else []))
            expected += 1
            new_opinion_pending = False
        elif number == 1 and new_opinion_pending:
            opinion += 1
            paragraphs.append((opinion, 1, [match.group(2)] if match.group(2) else []))
            expected = 2
            new_opinion_pending = False
        elif paragraphs:
            paragraphs[-1][2].append(text)
        else:
            preamble.append(text)
    if preamble and paragraphs:
        paragraphs[0][2][:0] = preamble
    return [
        ParsedParagraph(seq, op, paragraph_label(op, num), False, join_lines(body))
        for seq, (op, num, body) in enumerate(paragraphs, start=1)
        if join_lines(body)
    ]


def _derived_paragraphs(lines: list[Line]) -> list[ParsedParagraph]:
    blocks: list[list[str]] = []
    last_block = None
    for line in lines:
        if _HEADING_LINE.match(line.text) or _AUTHOR_LINE.match(line.text):
            continue
        if line.block != last_block:
            blocks.append([])
            last_block = line.block
        blocks[-1].append(line.text)
    merged: list[str] = []
    carry = ""
    for block in blocks:
        text = join_lines([carry, join_lines(block)]) if carry else join_lines(block)
        if len(text) < _MIN_DERIVED_CHARS:
            carry = text
            continue
        merged.append(text)
        carry = ""
    if carry:
        if merged:
            merged[-1] = join_lines([merged[-1], carry])
        else:
            merged.append(carry)
    return [ParsedParagraph(i, 0, str(i), True, text) for i, text in enumerate(merged, start=1)]


def _cut_body(lines: list[Line]) -> tuple[list[Line], str | None]:
    """Stop the body at the reporter's 'Result of the Case' line; return (body, result)."""
    for i, line in enumerate(lines):
        lower = line.text.lower()
        if lower.startswith(_RESULT):
            result = line.text[len(_RESULT) :].strip()
            return lines[:i], result or None
        if lower.startswith(_STOP):
            return lines[:i], None
    return lines, None


def parse_judgment(lines: list[Line]) -> ParsedJudgment:
    front, body = _split_front_and_body(lines)
    front_matter, header = _parse_front_matter(front)
    bench, author = parse_bench(join_lines(header))
    body, result = _cut_body(body)
    if result:
        front_matter["result"] = result
    paragraphs = _numbered_paragraphs(body)
    if len(paragraphs) < 2:
        paragraphs = _derived_paragraphs(body)
    return ParsedJudgment(
        bench=bench,
        author=author,
        case_name=parse_case_name(header),
        front_matter=front_matter,
        paragraphs=paragraphs,
    )
