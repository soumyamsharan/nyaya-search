"""Descriptions and official links for statutes and provisions. Descriptions show only once reviewed."""

from functools import lru_cache
from importlib import resources
from urllib.parse import quote

import yaml


@lru_cache
def _descriptions() -> dict:
    text = resources.files("nyaya.data").joinpath("descriptions.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text).get("statutes", {}) or {}


def reviewed_description(statute_key: str) -> dict | None:
    """The description and reviewer for a statute, or None if it has not been reviewed."""
    entry = _descriptions().get(statute_key) or {}
    if not entry.get("description") or not entry.get("reviewed_by") or not entry.get("reviewed_on"):
        return None
    return {"text": entry["description"], "reviewed_by": entry["reviewed_by"], "reviewed_on": str(entry["reviewed_on"])}


def official_search_url(name: str) -> str:
    """India Code's search for a name. Links to their search, never to item identifiers (see the hyperlink policy)."""
    return f"https://indiacode.gov.in/search?query={quote(name)}"
