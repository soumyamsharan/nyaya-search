"""Every kind of statute reference in judgment text: Act sections, Constitution articles, rules (under their parent
Act), regulations and notifications. Pure functions; the same code runs in the pipeline and on judgment pages."""

import re
from dataclasses import dataclass

from nyaya.text import statute_key

CONSTITUTION_KEY = "constitution-of-india"
UNPARENTED_RULES_KEY = "rules-parent-not-identified"
_ROMAN = re.compile(r"^[IVXLC]+$")

# The Act or Rules name after "of the", e.g. "Code of Civil Procedure, 1908" or
# "Companies (Acceptance of Deposits) Rules, 2014".
_PARENT_NAME = (
    r"(?P<parent>(?:(?:[A-Z][A-Za-z()&,.'-]*|of|and|the|for|in|on)\s+){0,8}"
    r"(?:Act|Code|Sanhita|Adhiniyam|Rules|Regulations|Procedure|Constitution|Evidence)"
    r"(?:,?\s*(?:18|19|20)\d{2})?)"
)

_ARTICLE = re.compile(
    r"\bArticles?\s+(?P<nums>\d{1,3}[A-Z]?(?:\s*\([a-z0-9]{1,6}\))*(?:\s*(?:,|and|&)\s*\d{1,3}[A-Z]?(?:\s*\([a-z0-9]{1,6}\))*)*)"
    r"\s+of\s+the\s+Constitution\b"
)
_RULE = re.compile(
    r"(?:\bOrder\s+(?P<order>[IVXLC]+)\s*,?\s*)?\bRules?\s+(?P<num>\d{1,3}[A-Z]?(?:\s*\([a-z0-9]{1,6}\))*)"
    r"\s+of\s+the\s+" + _PARENT_NAME
)
_REGULATION = re.compile(
    r"\bRegulations?\s+(?P<num>\d{1,3}[A-Z]?(?:\s*\([a-z0-9]{1,6}\))*)\s+of\s+the\s+" + _PARENT_NAME
)
_NOTIFICATION = re.compile(
    r"\b(?P<what>Notification|Ordinance)\s+(?:No\.?\s*)?(?P<num>\d{1,4}\s*/\s*\d{2,4}|\d{1,4}\s+of\s+(?:18|19|20)\d{2})"
)


@dataclass(frozen=True)
class StatuteMention:
    kind: str  # section | article | rule | regulation | notification
    key: str  # the Act (or Constitution, or notifications) the reference belongs to
    name: str  # the name as printed
    number: str  # the provision number as printed: "138", "21", "Order XII Rule 6", "138"
    slug: str  # URL form: "138", "21", "xii-6"
    raw: str  # the text as it appears in the paragraph


def _clean_slug(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def find_all_statute_refs(text: str) -> list[StatuteMention]:
    from nyaya.text import find_statute_references

    found: list[StatuteMention] = []
    for m in find_statute_references(text):
        found.append(StatuteMention("section", m.key, m.name, m.section, m.section.lower(), m.raw))

    for m in _ARTICLE.finditer(text):
        for num in re.findall(r"\d{1,3}[A-Z]?", m.group("nums")):
            found.append(
                StatuteMention("article", CONSTITUTION_KEY, "Constitution of India", num, num.lower(), m.group(0))
            )

    for m in _RULE.finditer(text):
        parent_key = statute_key(m.group("parent"))
        num = _clean_slug(m.group("num"))
        order = m.group("order")
        number = f"Order {order} Rule {m.group('num')}" if order and _ROMAN.match(order) else f"Rule {m.group('num')}"
        slug = f"{order.lower()}-{num}" if order and _ROMAN.match(order) else num
        if parent_key:
            parent_name = m.group("parent").strip(" ,.").split(",")[0]
            found.append(StatuteMention("rule", parent_key, parent_name, number, slug, m.group(0)))

    for m in _REGULATION.finditer(text):
        parent_key = statute_key(m.group("parent"))
        if parent_key:
            num = _clean_slug(m.group("num"))
            found.append(StatuteMention("regulation", parent_key, m.group("parent").strip(" ,.").split(",")[0],
                                        f"Regulation {m.group('num')}", num, m.group(0)))

    for m in _NOTIFICATION.finditer(text):
        what = m.group("what")
        num = re.sub(r"\s+", "", m.group("num")).replace("of", "-").replace("/", "-")
        found.append(StatuteMention("notification", "notifications", what, f"{what} No. {m.group('num')}",
                                    num, m.group(0)))
    return found
