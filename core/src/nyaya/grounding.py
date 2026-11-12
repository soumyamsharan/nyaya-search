"""Grounding: every generated sentence must cite supplied paragraphs that support it, and must not name
cases or citations that are absent from those paragraphs. Anything else is dropped before display."""

import re
from dataclasses import dataclass

from nyaya.domain import CitedSentence, Paragraph, ParagraphRef
from nyaya.ml import Reranker
from nyaya.text import extract_citations, find_case_names, squash

_INLINE_REF = re.compile(r"\s*\[(?:P|¶|Para\s*)?\d+(?:\s*,\s*(?:P|¶)?\d+)*\]")


@dataclass(frozen=True)
class GeneratedSentence:
    text: str
    paras: list[int]


def _as_int(value: object) -> int | None:
    digits = re.sub(r"\D", "", str(value))
    return int(digits) if digits else None


def parse_sentences(items: object) -> list[GeneratedSentence]:
    """Tolerantly read [{"text": ..., "paras": [...]}] from model output; malformed items are skipped."""
    if not isinstance(items, list):
        return []
    sentences = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            continue
        paras = item.get("paras") or []
        paras = paras if isinstance(paras, list) else [paras]
        refs = [n for n in (_as_int(p) for p in paras) if n is not None]
        text = _INLINE_REF.sub("", item["text"]).strip()
        if text:
            sentences.append(GeneratedSentence(text, refs))
    return sentences


class GroundingFilter:
    def __init__(self, reranker: Reranker, support_threshold: float) -> None:
        self._reranker = reranker
        self._threshold = support_threshold

    def apply(
        self, sentences: list[GeneratedSentence], context: dict[int, Paragraph]
    ) -> tuple[list[CitedSentence], int]:
        """Return (kept sentences, number dropped)."""
        context_text = " ".join(p.text for p in context.values())
        context_citations = {c.norm for c in extract_citations(context_text)}
        squashed_context = squash(context_text)
        kept: list[CitedSentence] = []
        for sentence in sentences:
            refs = [n for n in dict.fromkeys(sentence.paras) if n in context]
            if not refs or len(refs) != len(set(sentence.paras)):
                continue  # uncited, or cites a paragraph that was not supplied
            if any(c.norm not in context_citations for c in extract_citations(sentence.text)):
                continue  # citation not present in the supplied paragraphs
            if any(squash(name) not in squashed_context for name in find_case_names(sentence.text)):
                continue  # case name not present in the supplied paragraphs
            scores = self._reranker.score(sentence.text, [context[n].text for n in refs])
            if max(scores, default=0.0) < self._threshold:
                continue  # cited paragraphs do not support the sentence
            kept.append(
                CitedSentence(
                    text=sentence.text, paragraphs=[ParagraphRef(seq=n, label=context[n].label) for n in refs]
                )
            )
        return kept, len(sentences) - len(kept)
