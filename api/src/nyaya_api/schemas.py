"""Request and error schemas. Response bodies are the core domain models."""

from datetime import date
from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, Field, field_validator, model_validator

from nyaya.domain import Outcome, Role, SearchFilters, SearchMode

MAX_QUERY_CHARS = 2000
MAX_QUESTION_CHARS = 1000

JudgmentId = Annotated[str, Path(pattern=r"^[0-9A-Za-z_]{3,40}$", description="Judgment id, e.g. 2024_10_108_125")]


def _not_blank(value: str, what: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{what} must not be empty")
    return value


class SearchParams(BaseModel):
    q: str = Field(max_length=MAX_QUERY_CHARS, description="Facts and issue in plain words, a quoted phrase, "
                                                           "or a citation")
    year_from: int | None = Field(default=None, ge=1950, le=2100)
    year_to: int | None = Field(default=None, ge=1950, le=2100)
    date_from: date | None = Field(default=None, description="Decided on or after (YYYY-MM-DD)")
    date_to: date | None = Field(default=None, description="Decided on or before (YYYY-MM-DD)")
    judge: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list, max_length=5, description="Repeatable; every judge must be on the bench"
    )
    author: str | None = Field(default=None, max_length=100, description="Judge who wrote the judgment")
    outcome: Outcome | None = None
    role: list[Role] = Field(default_factory=list, description="Repeatable; match only paragraphs with these roles")
    act: str | None = Field(default=None, max_length=200)
    section: str | None = Field(default=None, max_length=20, pattern=r"^\s*\d{1,4}[A-Za-z]{0,2}\s*$")
    mode: SearchMode | None = Field(default=None, description="Retrieval strategy (for evaluation)")

    @field_validator("q")
    @classmethod
    def _q(cls, value: str) -> str:
        return _not_blank(value, "Search query")

    @model_validator(mode="after")
    def _ranges(self) -> "SearchParams":
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError("year_from must not be after year_to")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self

    def filters(self) -> SearchFilters:
        return SearchFilters(
            year_from=self.year_from,
            year_to=self.year_to,
            date_from=self.date_from,
            date_to=self.date_to,
            judges=self.judge,
            author=self.author,
            outcome=self.outcome,
            roles=self.role,
            act=self.act,
            section=self.section,
        )


class QuestionRequest(BaseModel):
    question: str = Field(max_length=MAX_QUESTION_CHARS)

    @field_validator("question")
    @classmethod
    def _question(cls, value: str) -> str:
        return _not_blank(value, "Question")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Health(BaseModel):
    status: str
