"""Plain-language descriptions and official India Code links for statutes and provisions."""

from functools import lru_cache
from importlib import resources
from urllib.parse import quote

import yaml


@lru_cache
def _descriptions() -> dict:
    text = resources.files("nyaya.data").joinpath("descriptions.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text).get("statutes", {}) or {}


def description_for(statute_key: str) -> str | None:
    """The plain-language description of a statute, or None when none has been written."""
    return (_descriptions().get(statute_key) or {}).get("description") or None


def official_search_url(name: str) -> str:
    """India Code's search for a name. Links to their search, never to item identifiers (see the hyperlink policy)."""
    return f"https://indiacode.gov.in/search?query={quote(name)}"
