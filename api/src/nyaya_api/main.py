"""FastAPI application factory and server entry point."""

import json
import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from nyaya.config import Settings, get_settings
from nyaya.container import Services, build_services
from nyaya_api.errors import register_error_handlers
from nyaya_api.ratelimit import RateLimiter
from nyaya_api.routes import health, v1

log = logging.getLogger("nyaya.api")


async def _access_log(request: Request, call_next: Callable) -> Response:
    """Metadata only: method, route template, status, latency. Never the query string or body."""
    started = time.monotonic()
    response = await call_next(request)
    route = request.scope.get("route")
    log.info(json.dumps({
        "method": request.method,
        "route": getattr(route, "path", "unmatched"),
        "status": response.status_code,
        "ms": int((time.monotonic() - started) * 1000),
    }))
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = services or build_services(settings)
        yield
        app.state.services.close()

    app = FastAPI(title="Nyaya Search API", version="1.0.0", lifespan=lifespan)
    app.state.rate_limiter = RateLimiter(settings.rate_limit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.middleware("http")(_access_log)
    register_error_handlers(app)
    app.include_router(health)
    app.include_router(v1)
    return app


def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(
        create_app(settings),
        host="0.0.0.0",  # noqa: S104 - inside a container; only the reverse proxy can reach it
        port=8000,
        access_log=False,  # uvicorn's access log would include query strings
        proxy_headers=True,
        forwarded_allow_ips=settings.trusted_proxy_ips,
    )
