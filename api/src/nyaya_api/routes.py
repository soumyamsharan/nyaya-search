"""REST resources. Handlers only translate HTTP to service calls; logic lives in the core services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response

from nyaya.container import Services
from nyaya.domain import (
    Answer,
    Breakdown,
    CitationGraph,
    JudgeList,
    Judgment,
    NoteCreate,
    NoteCreated,
    NoteRenewed,
    Provision,
    SearchResponse,
    SharedNote,
    StatuteActPage,
    StatuteIndex,
    StatuteSectionPage,
)
from nyaya.errors import InvalidRequestError, NotFoundError
from nyaya.notes import NoteItem, resolve
from nyaya_api.ratelimit import enforce_rate_limit
from nyaya_api.schemas import ErrorResponse, Health, JudgmentId, QuestionRequest, SearchParams

NO_STORE = {"Cache-Control": "no-store"}
_ERRORS = {
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(services)]
v1 = APIRouter(prefix="/v1", responses=_ERRORS, dependencies=[Depends(enforce_rate_limit)])
health = APIRouter()  # not rate limited: uptime monitors must never be throttled


@health.get("/healthz", response_model=Health, tags=["health"])
def healthz(svc: ServicesDep) -> Health:
    svc.db.fetch_one("SELECT 1 AS ok")
    return Health(status="ok")


@v1.get("/search", response_model=SearchResponse, tags=["search"])
def search(params: Annotated[SearchParams, Query()], svc: ServicesDep, response: Response) -> SearchResponse:
    """Fact-pattern, phrase or citation search. Returns up to 10 judgments with the matching paragraph."""
    response.headers.update(NO_STORE)
    return svc.search.search(params.q, params.filters(), params.mode)


@v1.get("/judges", response_model=JudgeList, tags=["search"])
def list_judges(svc: ServicesDep) -> JudgeList:
    """Every judge on a bench in the corpus, with judgment counts (for name suggestions)."""
    return JudgeList(judges=svc.judgments.judges())


@v1.get("/statutes", response_model=StatuteIndex, tags=["statutes"])
def list_statutes(svc: ServicesDep) -> StatuteIndex:
    """Acts referred to in the judgments, with the sections referred to and how many judgments refer to each."""
    return svc.statutes.index()


@v1.get("/statutes/{key}", response_model=StatuteActPage, tags=["statutes"])
def get_statute_act(
    key: Annotated[str, Path(pattern=r"^[a-z0-9-]{3,80}$")],
    svc: ServicesDep,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
) -> StatuteActPage:
    """Every judgment that refers to any section of this Act, newest first, 25 per page."""
    result = svc.statutes.act_page(key, page, 25)
    if result is None:
        raise NotFoundError("no judgments refer to this Act")
    return result


@v1.get("/statutes/{key}/sections/{section}", response_model=StatuteSectionPage, tags=["statutes"])
def get_statute_section(
    key: Annotated[str, Path(pattern=r"^[a-z0-9-]{3,80}$")],
    section: Annotated[str, Path(pattern=r"^\d{1,4}[A-Za-z]{0,2}$")],
    svc: ServicesDep,
) -> StatuteSectionPage:
    """Judgments that refer to this section of this Act, each with the paragraphs where it does so."""
    page = svc.statutes.section(key, section)
    if page is None:
        raise NotFoundError("no judgments refer to this section")
    return page


PROVISION_KIND = Annotated[str, Path(pattern=r"^(section|article|rule|regulation|notification)$")]


@v1.get("/provisions/{kind}/{key}/{slug}", response_model=Provision, tags=["statutes"])
def get_provision(
    kind: PROVISION_KIND,
    key: Annotated[str, Path(pattern=r"^[a-z0-9-]{3,80}$")],
    slug: Annotated[str, Path(pattern=r"^[a-z0-9-]{1,40}$")],
    svc: ServicesDep,
) -> Provision:
    """One provision (section, article, rule, regulation or notification): the judgments that refer to it,
    related judgments that refer to other provisions of the same Act, and its India Code search link."""
    result = svc.statutes.provision(kind, key, slug)
    if result is None:
        raise NotFoundError("no judgments refer to this provision")
    return result


NOTE_ID = Annotated[str, Path(pattern=r"^[0-9a-f-]{36}$", description="Shared note id")]
OwnerToken = Annotated[str, Header(alias="X-Note-Token", min_length=20, max_length=200)]


@v1.post("/notes", response_model=NoteCreated, status_code=201, tags=["notes"])
def create_note(body: NoteCreate, svc: ServicesDep, response: Response) -> NoteCreated:
    """Save references to corpus paragraphs as a read-only shared note. Only references are stored, never text."""
    response.headers.update(NO_STORE)
    missing = [r.judgment_id for r in body.items if not svc.judgments.exists(r.judgment_id)]
    if missing:
        raise InvalidRequestError(f"unknown judgment: {missing[0]}")
    created = svc.notes.create([NoteItem(r.judgment_id, r.label) for r in body.items])
    return NoteCreated(id=created.id, owner_token=created.owner_token, expires_at=created.expires_at)


@v1.get("/notes/{note_id}", response_model=SharedNote, tags=["notes"])
def get_note(note_id: NOTE_ID, svc: ServicesDep, response: Response) -> SharedNote:
    """A shared note, read from the corpus. Revoked and expired notes return 410 note_withdrawn."""
    response.headers.update(NO_STORE)
    items, expires_at = svc.notes.read(note_id)
    return SharedNote(id=note_id, expires_at=expires_at, items=resolve(items, svc.judgments))


@v1.post("/notes/{note_id}/renewal", response_model=NoteRenewed, tags=["notes"])
def renew_note(note_id: NOTE_ID, svc: ServicesDep, token: OwnerToken) -> NoteRenewed:
    """Extend a note's life by 30 days. Requires the owner token."""
    return NoteRenewed(expires_at=svc.notes.renew(note_id, token))


@v1.delete("/notes/{note_id}", status_code=204, tags=["notes"])
def revoke_note(note_id: NOTE_ID, svc: ServicesDep, token: OwnerToken) -> Response:
    """Withdraw a shared note so its link shows nothing. Requires the owner token."""
    svc.notes.revoke(note_id, token)
    return Response(status_code=204)


@v1.get("/judgments/{judgment_id}", response_model=Judgment, tags=["judgments"])
def get_judgment(judgment_id: JudgmentId, svc: ServicesDep) -> Judgment:
    judgment = svc.judgments.get(judgment_id)
    if judgment is None:
        raise NotFoundError("judgment not found")
    return judgment


@v1.get("/judgments/{judgment_id}/breakdown", response_model=Breakdown, tags=["judgments"])
def get_breakdown(judgment_id: JudgmentId, svc: ServicesDep) -> Breakdown:
    """Headnote-style breakdown; generated on first request and cached."""
    return svc.breakdowns.get(judgment_id)


@v1.post("/judgments/{judgment_id}/questions", response_model=Answer, tags=["judgments"])
def ask_question(
    judgment_id: JudgmentId, body: QuestionRequest, svc: ServicesDep, response: Response
) -> Answer:
    """Answer a question from this judgment's text only. The question is not stored."""
    response.headers.update(NO_STORE)
    return svc.questions.ask(judgment_id, body.question)


@v1.get("/judgments/{judgment_id}/citations", response_model=CitationGraph, tags=["judgments"])
def get_citations(judgment_id: JudgmentId, svc: ServicesDep) -> CitationGraph:
    if not svc.judgments.exists(judgment_id):
        raise NotFoundError("judgment not found")
    return svc.citations.graph(judgment_id)
