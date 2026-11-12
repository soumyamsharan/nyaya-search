"""REST resources. Handlers only translate HTTP to service calls; logic lives in the core services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from nyaya.container import Services
from nyaya.domain import Answer, Breakdown, CitationGraph, JudgeList, Judgment, SearchResponse
from nyaya.errors import NotFoundError
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
