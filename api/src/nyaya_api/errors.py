"""One place that maps errors to HTTP responses with a consistent body: {"error": {"code", "message"}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from nyaya.errors import InvalidRequestError, LlmBusyError, LlmUnavailableError, NotFoundError, NyayaError
from nyaya_api.ratelimit import RateLimitedError

log = logging.getLogger("nyaya.api")

_STATUS = {
    NotFoundError: 404,
    InvalidRequestError: 422,
    RateLimitedError: 429,
    LlmBusyError: 503,
    LlmUnavailableError: 503,
}
RETRY_AFTER_SECONDS = {RateLimitedError: "60", LlmBusyError: "3600", LlmUnavailableError: "60"}


def error_response(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status, headers=headers)


def _validation_message(exc: RequestValidationError) -> str:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
    return f"{field}: {first.get('msg', 'invalid value')}".replace("Value error, ", "")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NyayaError)
    async def _domain(_: Request, exc: NyayaError) -> JSONResponse:
        kind = type(exc)
        retry = RETRY_AFTER_SECONDS.get(kind)
        return error_response(
            _STATUS.get(kind, 400), exc.code, str(exc), {"Retry-After": retry} if retry else None
        )

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "invalid_request", _validation_message(exc))

    @app.exception_handler(ValueError)
    async def _value(_: Request, exc: ValueError) -> JSONResponse:
        return error_response(422, "invalid_request", str(exc))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.scope.get("route", request.url.path))
        return error_response(500, "internal_error", "Something went wrong. Please try again.")
