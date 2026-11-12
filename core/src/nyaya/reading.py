"""Reading features: the cached headnote-style breakdown and grounded follow-up questions."""

from nyaya.domain import Answer, Breakdown, Paragraph, SearchFilters
from nyaya.errors import LlmUnavailableError, NotFoundError
from nyaya.grounding import GroundingFilter, parse_sentences
from nyaya.llm import GuardedLlm
from nyaya.repos import BreakdownCache, JudgmentRepository
from nyaya.search import SearchService
from nyaya.text import approx_tokens, headnote_paragraph_refs, parse_query

BREAKDOWN_PROMPT_VERSION = "breakdown-v3"
QA_PROMPT_VERSION = "qa-v1"
QA_CONTEXT_PARAGRAPHS = 8
QA_EDGE_PARAGRAPHS = 2  # opening and closing paragraphs usually state the issue and the decision
EDGE_PARAGRAPHS = 5
SECTIONS = ("facts", "issues", "held", "ratio")
NOT_ADDRESSED = "This judgment does not appear to address that question."
NO_SUPPORTED_ANSWER = "No answer supported by this judgment's text could be found."

_RULES = (
    "Use ONLY the numbered paragraphs provided. Never use outside knowledge, never name a case or citation "
    "that does not appear in the paragraphs, and never invent paragraph numbers. Every sentence must cite "
    "the numbers of the paragraphs that support it (the number inside [P...]). Reply with JSON only."
)
BREAKDOWN_SYSTEM = (
    "You write headnote-style breakdowns of Indian Supreme Court judgments for lawyers. " + _RULES + " "
    "Fill ALL four sections, each with 1 to 4 short sentences: "
    "facts = what happened and how the case reached this Court; "
    "issues = the legal questions the Court had to decide; "
    "held = what the Court decided and the orders it passed; "
    "ratio = the legal principle the decision rests on. "
    "For each sentence, \"paras\" lists 1 to 3 paragraph numbers copied from the [P<number>] tags above the "
    "paragraphs that state it. Never cite a number that has no [P<number>] tag in the text, and never cite ranges. "
    "Leave a section empty only if the paragraphs truly say nothing about it. Format (numbers are placeholders): "
    '{"facts": [{"text": "...", "paras": [1]}], "issues": [{"text": "...", "paras": [1]}], '
    '"held": [{"text": "...", "paras": [1]}], "ratio": [{"text": "...", "paras": [1]}]}'
)
QA_SYSTEM = (
    "You answer a lawyer's question about one Indian Supreme Court judgment. " + _RULES + " If the paragraphs "
    'do not answer the question, set "answerable" to false and give no sentences. Format: '
    '{"answerable": true, "sentences": [{"text": "...", "paras": [12]}]}. At most 5 sentences.'
)


def format_context(paragraphs: list[Paragraph]) -> str:
    return "\n\n".join(f"[P{p.seq}] {p.text}" for p in paragraphs)


def select_breakdown_paragraphs(
    paragraphs: list[Paragraph], headnote_labels: list[int], token_budget: int
) -> list[Paragraph]:
    """Headnote-referenced paragraphs first, then the opening and closing ones, then the rest in order,
    until the budget is used. Returned in document order."""
    by_label = {p.label: p for p in paragraphs}
    priority = [by_label[str(n)] for n in headnote_labels if str(n) in by_label]
    priority += paragraphs[:EDGE_PARAGRAPHS] + paragraphs[-EDGE_PARAGRAPHS:] + paragraphs
    chosen: dict[int, Paragraph] = {}
    used = 0
    for p in priority:
        if p.seq in chosen:
            continue
        cost = approx_tokens(p.text) + 4
        if used + cost > token_budget:
            continue
        chosen[p.seq] = p
        used += cost
    return [chosen[seq] for seq in sorted(chosen)]


class BreakdownService:
    def __init__(
        self,
        judgments: JudgmentRepository,
        cache: BreakdownCache,
        llm: GuardedLlm,
        grounding: GroundingFilter,
        token_budget: int,
    ) -> None:
        self._judgments = judgments
        self._cache = cache
        self._llm = llm
        self._grounding = grounding
        self._token_budget = token_budget

    def get(self, judgment_id: str) -> Breakdown:
        if not self._judgments.exists(judgment_id):
            raise NotFoundError("judgment not found")
        cached = self._cache.latest(judgment_id, BREAKDOWN_PROMPT_VERSION)
        if cached:
            return Breakdown.model_validate(cached)
        paragraphs = self._judgments.paragraphs(judgment_id)
        headnotes = self._judgments.front_matter(judgment_id).get("headnotes", "")
        context = select_breakdown_paragraphs(paragraphs, headnote_paragraph_refs(headnotes), self._token_budget)
        by_seq = {p.seq: p for p in context}

        def ground(content: dict) -> tuple[Breakdown, int]:
            sections, dropped = {}, 0
            for name in SECTIONS:
                generated = parse_sentences(content.get(name))
                sections[name], lost = self._grounding.apply(generated, by_seq)
                dropped += lost
            if not any(sections.values()):
                raise LlmUnavailableError("no supported breakdown could be produced")
            return Breakdown(**sections, model=self._llm.model), dropped

        breakdown = self._llm.run(
            "breakdown", BREAKDOWN_PROMPT_VERSION, BREAKDOWN_SYSTEM, format_context(context), ground
        )
        self._cache.put(judgment_id, BREAKDOWN_PROMPT_VERSION, self._llm.model, breakdown.model_dump())
        return breakdown


class QuestionService:
    def __init__(
        self, judgments: JudgmentRepository, search: SearchService, llm: GuardedLlm, grounding: GroundingFilter
    ) -> None:
        self._judgments = judgments
        self._search = search
        self._llm = llm
        self._grounding = grounding

    def ask(self, judgment_id: str, question: str) -> Answer:
        if not self._judgments.exists(judgment_id):
            raise NotFoundError("judgment not found")
        context = self._context(judgment_id, question)
        if not context:
            return Answer(answered=False, sentences=[], message=NOT_ADDRESSED)
        by_seq = {p.seq: p for p in context}

        def ground(content: dict) -> tuple[Answer, int]:
            generated = parse_sentences(content.get("sentences"))
            if content.get("answerable") is False:
                return Answer(answered=False, sentences=[], message=NOT_ADDRESSED), len(generated)
            kept, dropped = self._grounding.apply(generated, by_seq)
            if not kept:
                return Answer(answered=False, sentences=[], message=NO_SUPPORTED_ANSWER), dropped
            return Answer(answered=True, sentences=kept), dropped

        user = f"Question: {question}\n\nParagraphs:\n{format_context(context)}"
        return self._llm.run("question", QA_PROMPT_VERSION, QA_SYSTEM, user, ground)

    def _context(self, judgment_id: str, question: str) -> list[Paragraph]:
        """The best-ranked paragraphs for the question (no relevance cut-off) plus the opening and closing
        paragraphs, in document order. The model, then grounding, decide whether they answer it."""
        hits = self._search.rank(
            parse_query(question),
            SearchFilters(judgment_id=judgment_id),
            self._search.default_mode,
            per_judgment=False,
            relevance_cutoff=False,
        )[:QA_CONTEXT_PARAGRAPHS]
        ranked = [p for _, p in self._judgments.paragraphs_by_ids(h.paragraph_id for h in hits).values()]
        everything = self._judgments.paragraphs(judgment_id)
        edges = everything[:QA_EDGE_PARAGRAPHS] + everything[-QA_EDGE_PARAGRAPHS:]
        return sorted({p.seq: p for p in ranked + edges}.values(), key=lambda p: p.seq)
