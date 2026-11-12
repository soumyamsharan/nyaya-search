"""Spelling help from the corpus's own vocabulary: which query words are unknown, and a corrected query."""

import re

from nyaya.db import Database

KNOWN_MIN_FREQ = 3  # a word seen this often in the judgments counts as correctly spelled
CANDIDATE_MIN_FREQ = 5  # corrections must be at least this common
MIN_WORD_LENGTH = 4  # shorter words are left alone (too many near neighbours)
MAX_EDITS = 2
_OPERATORS = {"AND", "OR", "NOT"}
_WORD = re.compile(r"[A-Za-z]+")


def candidate_words(raw: str) -> list[str]:
    """Words worth checking: alphabetic, long enough, not operators."""
    return [w for w in _WORD.findall(raw) if len(w) >= MIN_WORD_LENGTH and w not in _OPERATORS]


def apply_corrections(raw: str, corrections: dict[str, str]) -> str:
    """Replace misspelled words in the raw query, keeping operators, quotes and everything else as typed."""

    def replace(match: re.Match) -> str:
        word = match.group(0)
        fixed = corrections.get(word.lower())
        if not fixed or word in _OPERATORS:
            return word
        return fixed.capitalize() if word[0].isupper() and not word.isupper() else fixed

    return _WORD.sub(replace, raw)


class SpellingCorrector:
    def __init__(self, db: Database) -> None:
        self._db = db

    def unknown_words(self, raw: str) -> list[str]:
        words = sorted({w.lower() for w in candidate_words(raw)})
        if not words:
            return []
        known = {
            r["word"]
            for r in self._db.fetch_all(
                "SELECT word FROM vocabulary WHERE word = ANY(%s) AND freq >= %s", [words, KNOWN_MIN_FREQ]
            )
        }
        return [w for w in words if w not in known]

    def correction(self, word: str) -> str | None:
        """Closest common corpus word: fewest edits, then swapped letters (same letters), then trigram similarity
        weighted by how common the word is. Candidates share the first letter and are within two letters in length."""
        row = self._db.fetch_one(
            """SELECT word FROM vocabulary
               WHERE freq >= %(min)s AND left(word, 1) = left(%(w)s, 1)
                 AND abs(length(word) - length(%(w)s)) <= %(edits)s AND levenshtein(word, %(w)s) <= %(edits)s
               ORDER BY levenshtein(word, %(w)s),
                        (SELECT string_agg(c, '' ORDER BY c) FROM regexp_split_to_table(word, '') c)
                          = (SELECT string_agg(c, '' ORDER BY c) FROM regexp_split_to_table(%(w)s, '') c) DESC,
                        similarity(word, %(w)s) * ln(freq + 1) DESC
               LIMIT 1""",
            {"w": word, "min": CANDIDATE_MIN_FREQ, "edits": MAX_EDITS},
        )
        return row["word"] if row else None

    def suggest(self, raw: str, unknown: list[str] | None = None) -> str | None:
        """Corrected query, or None when nothing could be corrected."""
        unknown = self.unknown_words(raw) if unknown is None else unknown
        corrections = {w: fixed for w in unknown if (fixed := self.correction(w)) and fixed != w}
        if not corrections:
            return None
        suggestion = apply_corrections(raw, corrections)
        return suggestion if suggestion != raw else None
