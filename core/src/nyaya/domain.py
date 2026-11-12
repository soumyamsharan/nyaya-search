"""Domain models shared by the pipeline, the API and the evals."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    """The job a paragraph does in a judgment (machine-assigned)."""

    FACTS = "facts"
    ISSUE = "issue"
    PETITIONER_ARGUMENT = "petitioner_argument"
    RESPONDENT_ARGUMENT = "respondent_argument"
    STATUTE = "statute"
    PRECEDENT = "precedent"
    REASONING = "reasoning"
    CONCLUSION = "conclusion"


class Outcome(StrEnum):
    ALLOWED = "allowed"
    PARTLY_ALLOWED = "partly_allowed"
    DISMISSED = "dismissed"
    DISPOSED = "disposed"
    OTHER = "other"


class SearchMode(StrEnum):
    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"
    HYBRID_RERANK = "hybrid_rerank"


class ParagraphRef(BaseModel):
    seq: int
    label: str


class CitationRef(BaseModel):
    """A citation found in a paragraph: the text as printed, and the judgment it resolves to (if held)."""

    raw: str
    judgment_id: str | None = None
    title: str | None = None
    citation: str | None = None


class StatuteRef(BaseModel):
    """A section of an Act mentioned in a paragraph, linked to its statute page."""

    raw: str
    key: str
    name: str
    section: str


class Paragraph(ParagraphRef):
    text: str
    label_derived: bool = False
    role: Role | None = None
    cites_cases: bool = False
    references: list[CitationRef] = Field(default_factory=list)
    statutes: list[StatuteRef] = Field(default_factory=list)


class JudgmentSummary(BaseModel):
    id: str
    title: str
    decision_date: date | None
    bench: list[str]
    citation: str | None = Field(description="Primary citation: neutral citation, else SCR")
    cited_by_count: int = 0


class FrontMatterSection(BaseModel):
    section: str
    title: str
    text: str


class Judgment(JudgmentSummary):
    author: str | None
    neutral_citation: str | None
    scr_citation: str | None
    disposal_nature: str | None
    pdf_url: str
    acts: list[str]
    reporter_front_matter: list[FrontMatterSection]
    paragraphs: list[Paragraph]
    numbering_derived: bool


class SearchFilters(BaseModel):
    year_from: int | None = None
    year_to: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    judge: str | None = None  # kept for old links; same as a one-item `judges`
    judges: list[str] = Field(default_factory=list)  # every one must be on the bench
    author: str | None = None
    outcome: Outcome | None = None
    roles: list[Role] = Field(default_factory=list)  # match only paragraphs with these roles
    act: str | None = None
    section: str | None = None
    judgment_id: str | None = None  # internal: restricts retrieval to one judgment (follow-up questions)


class SearchHit(BaseModel):
    """A retrieved paragraph before hydration."""

    paragraph_id: int
    judgment_id: str
    score: float


class SearchResult(BaseModel):
    judgment: JudgmentSummary
    matched_paragraph: Paragraph
    score: float


class SearchResponse(BaseModel):
    query_type: str  # fact_pattern | citation
    results: list[SearchResult]
    message: str | None = None
    suggestion: str | None = Field(default=None, description="Corrected query when words look misspelled")


class JudgeCount(BaseModel):
    name: str
    judgments: int


class JudgeList(BaseModel):
    judges: list[JudgeCount]


class CitedSentence(BaseModel):
    text: str
    paragraphs: list[ParagraphRef]


class Breakdown(BaseModel):
    facts: list[CitedSentence]
    issues: list[CitedSentence]
    held: list[CitedSentence]
    ratio: list[CitedSentence]
    model: str
    machine_generated: bool = True


class Answer(BaseModel):
    answered: bool
    sentences: list[CitedSentence]
    message: str | None = None
    machine_generated: bool = True


class CitationLink(BaseModel):
    judgment: JudgmentSummary
    paragraph: ParagraphRef = Field(description="Paragraph of the citing judgment")
    overruling_language: bool = False
    paragraph_text: str | None = None


class UnresolvedCitation(BaseModel):
    raw: str
    paragraph: ParagraphRef


class CitationGraph(BaseModel):
    cites: list[CitationLink]
    cited_by: list[CitationLink]
    unresolved: list[UnresolvedCitation]
    overruling_evidence: list[CitationLink]


class SectionCount(BaseModel):
    section: str
    judgments: int


class StatuteSummary(BaseModel):
    key: str
    name: str
    judgments: int
    sections: list[SectionCount]


class StatuteIndex(BaseModel):
    acts: list[StatuteSummary]


class StatuteParagraph(BaseModel):
    label: str
    text: str


class StatuteJudgment(BaseModel):
    judgment: JudgmentSummary
    paragraphs: list[StatuteParagraph]


class StatuteSectionPage(BaseModel):
    key: str
    name: str
    section: str
    judgments: list[StatuteJudgment]


class NoteRef(BaseModel):
    judgment_id: str
    label: str = Field(pattern=r"^[0-9A-Za-z]{1,8}(-[0-9A-Za-z]{1,8})?$", max_length=20)


class NoteCreate(BaseModel):
    items: list[NoteRef] = Field(min_length=1, max_length=200)


class NoteCreated(BaseModel):
    id: str
    owner_token: str = Field(description="Shown once. Needed to renew or revoke this note; keep it private.")
    expires_at: datetime


class NoteParagraph(BaseModel):
    judgment: JudgmentSummary | None
    label: str
    text: str | None = Field(description="Null when the paragraph no longer exists in the corpus")


class SharedNote(BaseModel):
    id: str
    expires_at: datetime
    items: list[NoteParagraph]


class NoteRenewed(BaseModel):
    expires_at: datetime


class ActJudgment(BaseModel):
    judgment: JudgmentSummary
    sections: list[str] = Field(description="Sections of this Act that the judgment refers to")


class StatuteActPage(BaseModel):
    key: str
    name: str
    judgments_total: int
    page: int
    per_page: int
    judgments: list[ActJudgment]
