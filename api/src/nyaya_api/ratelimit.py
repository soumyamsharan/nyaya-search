"""Per-client-IP rate limiting as a router dependency, so every /v1 route is covered and health checks are not."""

from fastapi import Request
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from nyaya.errors import NyayaError


class RateLimitedError(NyayaError):
    code = "rate_limited"


class RateLimiter:
    def __init__(self, rate: str) -> None:
        self._limit = parse(rate)
        self._limiter = MovingWindowRateLimiter(MemoryStorage())

    def check(self, client_ip: str) -> None:
        if not self._limiter.hit(self._limit, client_ip):
            raise RateLimitedError("Too many requests; please slow down.")


def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency. uvicorn sets request.client from X-Forwarded-For only for trusted proxies."""
    request.app.state.rate_limiter.check(request.client.host if request.client else "unknown")
