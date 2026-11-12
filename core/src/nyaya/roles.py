"""Rule-based paragraph role labelling: transparent cue phrases plus position in the judgment.

Rules are checked in order and the first match wins; anything unmatched falls back by position (before the first
argument or issue: facts; after it: reasoning). Deterministic, so re-running gives the same labels.
"""

import re
from collections.abc import Sequence

from nyaya.domain import Role
from nyaya.text import extract_citations, find_case_names

_ARGUMENTS = (Role.PETITIONER_ARGUMENT, Role.RESPONDENT_ARGUMENT)
CONCLUSION_ZONE = 0.8  # weaker disposal cues count only in the last 20% of paragraphs (and the last three)
STRONG_CONCLUSION_ZONE = 0.5  # explicit orders ("we allow the appeal", "set aside") count in the last half

_DISPOSAL = re.compile(
    r"\b(appeals?|petitions?|special leave petitions?|writ petitions?)\s+(?:is|are|stands?|shall stand)\s+"
    r"(?:accordingly\s+|hereby\s+|partly\s+)?(allowed|dismissed|disposed\s+of)\b"
    r"|\bimpugned (?:judgment|order)s?\b.{0,80}\b(?:set aside|quashed|upheld|affirmed)\b"
    r"|\b(?:is|are|stands?)\s+(?:accordingly\s+)?set aside\b|\b(?:is|are)\s+(?:hereby\s+)?directed\s+to\b"
    r"|\bno order as to costs\b|\bpending (?:interlocutory )?applications?,? if any\b|\bstand(?:s)? disposed of\b",
    re.I | re.S,
)
_STRONG_DISPOSAL = re.compile(
    r"\bwe\s+(?:are\s+)?(?:therefore\s+|accordingly\s+)?(?:inclined\s+to\s+)?(?:allow|dismiss|partly allow)\s+"
    r"(?:the|these|this|both)\s+(?:appeals?|petitions?)\b|\b(?:quashed|quash)\s+and\s+set\s+aside\b"
    r"|\b(?:appeals?|petitions?)\s+(?:is|are)\s+(?:accordingly\s+)?(?:allowed|dismissed|partly allowed)\b"
    r"|\bwe\s+(?:hereby\s+)?direct\b|\bis\s+commuted\b|\bstands?\s+(?:quashed|set aside)\b",
    re.I,
)
_COUNSEL = re.compile(
    r"\b(?:learned\s+)?(?:senior\s+)?(?:counsel|advocate|solicitor general|attorney general|amicus)"
    r"[^.]{0,80}?\b(?:for|on behalf of|appearing for|representing)\s+(?:the\s+)?(?P<side>[a-z-]+)",
    re.I,
)
_COUNSEL_ONLY = re.compile(
    r"\b(?:learned\s+)?(?:senior\s+)?counsel\b[^.]{0,40}\b(?:submitted|contended|argued|urged)\b"
    r"|\bit is (?:his|her|their|the appellants?'?s?|the respondents?'?s?) (?:submission|contention|case)\b"
    r"|\bit is sought to be (?:urged|contended|argued|submitted)\b"
    r"|\blearned (?:ASG|SG|AG|Additional Solicitor General|Solicitor General|Attorney General)\b[^.]{0,60}"
    r"\b(?:submitted|contended|argued|urged|relied)\b"
    r"|^(?:Mr\.|Ms\.|Mrs\.|Shri|Smt\.|Dr\.)\s+[A-Z][\w.]*(?:\s+[A-Z][\w.]*){0,2},?[^.]{0,80}?"
    r"\b(?:submitted|contended|argued|urged)\b",
    re.I,
)
_ARGUMENT_VERB = re.compile(
    r"\b(submit|submitted|submission|contend|contended|argue|argued|urged|canvassed|assail|relied|"
    r"pointed out|vehemently|per contra)\b",
    re.I,
)
_PETITIONER_SIDES = ("appellant", "petitioner", "complainant", "applicant", "plaintiff", "assessee")
_RESPONDENT_SIDES = ("respondent", "state", "accused", "defendant", "revenue", "union", "prosecution")
_PER_CONTRA = re.compile(r"\bper contra\b", re.I)
_ISSUE = re.compile(
    r"\b(?:questions?|issues?|points?)\s+(?:that|which)?\s*(?:arises?|arise|falls?|fall|requires?|come)s?\s+"
    r"(?:for\s+)?(?:our\s+)?(?:consideration|determination|decision)"
    r"|\b(?:short|moot|only|core|central|primary)\s+(?:question|issue)\b"
    r"|\bpoints? for determination\b|\bissues? (?:framed|involved)\b",
    re.I,
)
_STATUTE_CUE = re.compile(
    r"\b(?:reads?|read) as (?:under|follows)\b"
    r"|\b(?:is|are) (?:extracted|reproduced|quoted) (?:below|hereunder|as under)\b"
    r"|\bprovides as (?:under|follows)\b",
    re.I,
)
_SECTION_START = re.compile(r"^[“\"']?\s*(?:\d{1,4}[A-Z]?\.\s+[A-Z]|section\s+\d|rule\s+\d|article\s+\d)", re.I)
_CONTINUED_ARGUMENT = re.compile(
    r"^(?:\(?[ivx]+\)|\(?[a-z]\)|\d+(?:\.\d+)*\.?)?\s*(?:it\s+(?:was|is|has\s+been)\s+(?:further\s+|also\s+)?"
    r"(?:submitted|contended|argued|urged|pointed out)|(?:he|she|they|it|the\s+learned\s+(?:senior\s+)?counsel)"
    r"\s+(?:has\s+)?(?:further|also|then|lastly|finally)?\s*(?:submitted|submits|contended|argued|urged|relied|"
    r"placed reliance|referred)|(?:further|additionally|lastly|finally),?\s+(?:it\s+was\s+)?(?:submitted|contended|"
    r"argued|urged))",
    re.I,
)
_HOLDING = re.compile(r"\b(held|observed|ruled|laid down|opined|explained|reiterated|it is held)\b", re.I)
_PRECEDENT_CUE = re.compile(
    r"\(supra\)|\bin the case of\b|\b(?:this|the)\s+(?:Constitution\s+|Division\s+|Larger\s+|Seven-Judge\s+|"
    r"Three-Judge\s+|Full\s+)?(?:Court|Bench)\s+in\b|\bJustice\s+[A-Z]|\b[A-Z][a-z]+,\s*J\."
    r"|\bin paragraph\s+\d+\s+of\b",
)


UNSIDED = "unsided_argument"  # counsel's submission with no side named; takes the side of the last argument


def _quoted_share(text: str) -> float:
    quoted = sum(len(m) for m in re.findall(r"[“\"]([^”\"]{20,})[”\"]", text))
    return quoted / max(len(text), 1)


def _argument_role(text: str) -> Role | str | None:
    head = text[:400]
    if not _ARGUMENT_VERB.search(head):
        return None
    if _PER_CONTRA.search(head):
        return Role.RESPONDENT_ARGUMENT
    match = _COUNSEL.search(head)
    if not match:
        return UNSIDED if _COUNSEL_ONLY.search(head) else None
    side = match.group("side").lower()
    if side.startswith(_PETITIONER_SIDES):
        return Role.PETITIONER_ARGUMENT
    if side.startswith(_RESPONDENT_SIDES):
        return Role.RESPONDENT_ARGUMENT
    return None


def _cue_role(text: str, position: float, near_end: bool) -> Role | str | None:
    if (position >= CONCLUSION_ZONE or near_end) and _DISPOSAL.search(text):
        return Role.CONCLUSION
    if position >= STRONG_CONCLUSION_ZONE and _STRONG_DISPOSAL.search(text):
        return Role.CONCLUSION
    if role := _argument_role(text):
        return role
    about_other_case = bool(extract_citations(text) or find_case_names(text) or _PRECEDENT_CUE.search(text))
    if _ISSUE.search(text[:500]) and not about_other_case:
        return Role.ISSUE
    if (_STATUTE_CUE.search(text) and re.search(r"\b(section|rule|article|clause)\b", text, re.I)) or (
        _SECTION_START.match(text) and _quoted_share(text) > 0.5
    ):
        return Role.STATUTE
    if about_other_case and _HOLDING.search(text):
        return Role.PRECEDENT
    return None


def assign_roles(texts: Sequence[str]) -> list[Role]:
    """One role per paragraph text, in document order."""
    count = len(texts)
    cued: list[Role | None] = []
    last_side = Role.PETITIONER_ARGUMENT
    for i, text in enumerate(texts):
        role = _cue_role(text, position=i / max(count - 1, 1), near_end=i >= count - 3)
        previous = cued[-1] if cued else None
        if role == UNSIDED:
            role = last_side
        elif role is None and previous in _ARGUMENTS and _CONTINUED_ARGUMENT.match(text[:200]):
            role = previous  # "It was further submitted..." continues the same side's argument
        if role in _ARGUMENTS:
            last_side = role
        cued.append(role)
    first_argument = next((i for i, role in enumerate(cued) if role in (Role.ISSUE, *_ARGUMENTS)), None)
    boundary = first_argument if first_argument is not None else max(1, count // 3)
    return [role or (Role.FACTS if i < boundary else Role.REASONING) for i, role in enumerate(cued)]
