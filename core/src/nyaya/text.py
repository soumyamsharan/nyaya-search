"""Pure text utilities: citations, Act names, case names, query parsing. No I/O."""

import re
from dataclasses import dataclass, field

# --- Citations -------------------------------------------------------------------------------------

_SCC_ONLINE = re.compile(r"(?P<y>(?:19|20)\d{2})\s*SCC\s*Online\s*SC\s*(?P<p>\d{1,5})", re.I)
_SCC = re.compile(
    r"\((?P<y>(?:19|20)\d{2})\)\s*(?P<supp>Supp\.?\s*\(?(?P<sn>\d)?\)?\s*)?(?P<v>\d{1,2})?\s*"
    r"S\.?\s?C\.?\s?C\.?(?!\s*Online)\s*(?P<p>\d{1,4})",
    re.I,
)
_SCR = re.compile(
    r"\[(?P<y>(?:19|20)\d{2})\]\s*(?P<v>\d{1,2})?\s*(?P<supp>Supp\.?\s*)?S\.?\s?C\.?\s?R\.?\s*(?P<p>\d{1,4})",
    re.I,
)
_AIR = re.compile(r"AIR\s*(?P<y>(?:19|20)\d{2})\s*SC\s*(?P<p>\d{1,4})")
_INSC = re.compile(r"(?P<y>(?:19|20)\d{2})\s*INSC\s*(?P<p>\d{1,5})")

_PATTERNS = (("SCCOL", _SCC_ONLINE), ("SCC", _SCC), ("SCR", _SCR), ("AIR", _AIR), ("INSC", _INSC))


@dataclass(frozen=True)
class Citation:
    raw: str
    norm: str  # canonical key, e.g. "SCC|2007|3||755"
    start: int
    end: int


def _norm(reporter: str, m: re.Match) -> str:
    groups = m.groupdict()
    supp = ""
    if groups.get("supp"):
        supp = "S" + (groups.get("sn") or "")
    return "|".join([reporter, groups["y"], (groups.get("v") or "").strip(), supp, groups["p"]])


def extract_citations(text: str) -> list[Citation]:
    """Find reported and neutral citations in text, in order, without overlaps."""
    found: list[Citation] = []
    taken: list[tuple[int, int]] = []
    for reporter, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            found.append(Citation(m.group(0), _norm(reporter, m), m.start(), m.end()))
    return sorted(found, key=lambda c: c.start)


def normalize_citation(text: str) -> str | None:
    """Canonical key for a single citation string, or None if it is not one."""
    found = extract_citations(text)
    return found[0].norm if found else None


def is_citation_query(text: str) -> bool:
    """True when the whole query is one citation (allowing stray punctuation)."""
    found = extract_citations(text)
    if len(found) != 1:
        return False
    rest = (text[: found[0].start] + text[found[0].end :]).strip(" .,;:()[]")
    return not rest


# --- Overruling language ---------------------------------------------------------------------------

_OVERRULING = re.compile(
    r"\b(overrul(?:e|ed|es|ing)|no longer (?:good|valid) law|not (?:a )?good law|stands? overruled)\b", re.I
)


def has_overruling_language(text: str) -> bool:
    return bool(_OVERRULING.search(text))


# --- Acts ------------------------------------------------------------------------------------------


def normalize_act(name: str) -> str:
    """'The Negotiable Instruments Act, 1881.' -> 'negotiable instruments act 1881'."""
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", name.lower())
    words = [w for w in cleaned.split() if w != "the"]
    return " ".join(words)


_SECTION_OF_ACT = re.compile(
    r"\bSections?\s+(?P<sec>\d{1,4}[A-Z]{0,2})(?:\s*\([^)]{1,6}\))*\s+of\s+the\s+"
    r"(?P<act>(?:[A-Z][A-Za-z()&,.-]*\s+){0,8}?(?:Act|Code|Sanhita|Adhiniyam)(?:,?\s*\d{4})?)"
)


def find_section_references(text: str) -> list[tuple[str, str]]:
    """Return (act name, section) pairs for phrases like 'Section 138 of the Negotiable Instruments Act, 1881'."""
    return [(m.group("act").strip(" ,."), m.group("sec")) for m in _SECTION_OF_ACT.finditer(text)]


# --- Case names ------------------------------------------------------------------------------------

_CASE_NAME = re.compile(
    r"\b([A-Z][\w.&'-]*(?:\s+(?:[A-Z][\w.&'-]*|of|and|&))*)\s+(?:v\.|vs\.?|versus)\s+"
    r"([A-Z][\w.&'-]*(?:\s+(?:[A-Z][\w.&'-]*|of|and|&))*)"
)


def find_case_names(text: str) -> list[str]:
    return [m.group(0) for m in _CASE_NAME.finditer(text)]


_PARTY_LIST_SUFFIX = re.compile(r"\s+R\d+\s*:.*$", re.S)
_VERSUS_WORD = re.compile(r"\s+versus\s+", re.I)


def clean_case_title(title: str) -> str:
    """Metadata title -> citable name: drop appended 'R1: ... R2: ...' party lists, 'versus' -> 'v.'."""
    title = _PARTY_LIST_SUFFIX.sub("", " ".join(title.split()))
    return _VERSUS_WORD.sub(" v. ", title).strip()


def squash(text: str) -> str:
    """Lowercase alphanumerics only; used to compare names and phrases loosely."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


# --- Queries ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedQuery:
    """A search query split into ranking text and hard constraints.

    free_text: plain words used for ranking (keyword and semantic).
    phrases: quoted phrases (also required, and added to the ranking text).
    required: words or phrases that must appear in a matching paragraph (AND, quotes).
    excluded: words or phrases that must not appear (NOT).
    """

    raw: str
    free_text: str
    phrases: list[str] = field(default_factory=list)
    required: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.free_text and not self.required

    @property
    def rerank_text(self) -> str:
        return " ".join([self.free_text, *self.phrases]).strip()


_TOKEN = re.compile(r'"([^"]*)"|(\S+)')
_OPERATORS = {"AND", "OR", "NOT"}


@dataclass
class _Term:
    text: str
    phrase: bool
    required: bool
    excluded: bool


def parse_query(raw: str) -> ParsedQuery:
    """Parse quoted phrases and the upper-case operators AND, OR, NOT.

    Words are OR-ed by default; `a AND b` makes both required; `NOT x` excludes x; quoted phrases are
    required. Lower-case and/or/not are ordinary words.
    """
    terms: list[_Term] = []
    pending_and = pending_not = False
    for phrase, word in _TOKEN.findall(raw):
        if word in _OPERATORS:
            if word == "AND" and terms and not terms[-1].excluded:
                terms[-1].required = True
            pending_and = pending_and or word == "AND"
            pending_not = pending_not or word == "NOT"
            continue
        text = " ".join((phrase if not word else word.strip('"')).split())
        if not text:
            continue
        is_phrase = bool(phrase)
        terms.append(_Term(text, is_phrase, required=is_phrase or pending_and, excluded=pending_not))
        pending_and = pending_not = False
    kept = [t for t in terms if not t.excluded]
    return ParsedQuery(
        raw=raw,
        free_text=" ".join(t.text for t in kept if not t.phrase),
        phrases=[t.text for t in kept if t.phrase],
        required=[t.text for t in kept if t.required],
        excluded=[t.text for t in terms if t.excluded],
    )


_PARA_REF = re.compile(r"\[Paras?\.?\s*([^\]]+)\]", re.I)


def headnote_paragraph_refs(text: str) -> list[int]:
    """Paragraph numbers cited in reporter headnotes: '[Para 27]', '[Paras 21-23, 30]'."""
    numbers: list[int] = []
    for group in _PARA_REF.findall(text):
        for start, end in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", group):
            first = int(start)
            last = int(end) if end else first
            numbers.extend(range(first, min(last, first + 20) + 1))
    return list(dict.fromkeys(numbers))


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)
