import logging

import pytest
from fastapi.testclient import TestClient

from nyaya.config import Settings
from nyaya.domain import Answer
from nyaya.errors import LlmBusyError, LlmUnavailableError
from nyaya_api.main import create_app
from tests.fakes import FakeServices, judgment

ORIGIN = "https://nyaya-search.vercel.app"


def make_client(services: FakeServices | None = None, rate_limit: str = "100/minute") -> TestClient:
    settings = Settings(database_url="postgresql://unused", allowed_origins=[ORIGIN], rate_limit=rate_limit)
    return TestClient(create_app(settings, services or FakeServices(judgment=judgment())))


@pytest.fixture
def client():
    with make_client() as c:
        yield c


def test_search_ok_and_not_cached(client):
    response = client.get("/v1/search", params={"q": "cheque bounce notice", "year_from": 2024, "act": "NI Act"})
    assert response.status_code == 200
    assert response.json()["query_type"] == "fact_pattern"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("params", [{"q": "   "}, {"q": "x" * 2001}, {"q": "a", "year_from": 2025, "year_to": 2024},
                                    {"q": "a", "section": "drop table"}, {}])
def test_search_validation_errors_use_the_error_format(client, params):
    response = client.get("/v1/search", params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_judgment_found_and_not_found(client):
    assert client.get("/v1/judgments/2024_10_108_125").status_code == 200
    missing = client.get("/v1/judgments/2099_1_1_1")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"


def test_bad_judgment_id_is_rejected(client):
    assert client.get("/v1/judgments/..%2Fetc").status_code in (404, 422)


@pytest.mark.parametrize(("error", "code", "retry"), [(LlmBusyError("cap"), "llm_busy", "3600"),
                                                       (LlmUnavailableError("down"), "llm_unavailable", "60")])
def test_breakdown_busy_and_unavailable_are_503(error, code, retry):
    with make_client(FakeServices(judgment=judgment(), breakdown_error=error)) as c:
        response = c.get("/v1/judgments/2024_10_108_125/breakdown")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == code
    assert response.headers["retry-after"] == retry


def test_question_limits_and_answer(client):
    assert client.post("/v1/judgments/2024_10_108_125/questions", json={"question": "x" * 1001}).status_code == 422
    assert client.post("/v1/judgments/2024_10_108_125/questions", json={"question": " "}).status_code == 422
    ok = client.post("/v1/judgments/2024_10_108_125/questions", json={"question": "What was held?"})
    assert ok.status_code == 200 and ok.headers["cache-control"] == "no-store"


def test_citations_resource(client):
    assert client.get("/v1/judgments/2024_10_108_125/citations").json()["cited_by"] == []
    assert client.get("/v1/judgments/2099_1_1_1/citations").status_code == 404


def test_cors_allows_only_the_configured_origin(client):
    allowed = client.options("/v1/search", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"})
    assert allowed.headers.get("access-control-allow-origin") == ORIGIN
    other = client.options("/v1/search", headers={"Origin": "https://evil.example",
                                                  "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in other.headers


def test_rate_limit_returns_429_but_health_is_exempt():
    with make_client(rate_limit="2/minute") as c:
        codes = [c.get("/v1/search", params={"q": "a"}).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
        assert c.get("/v1/search", params={"q": "a"}).json()["error"]["code"] == "rate_limited"
        assert all(c.get("/healthz").status_code == 200 for _ in range(5))


def test_query_and_question_text_never_logged(caplog):
    services = FakeServices(judgment=judgment(), answer=Answer(answered=False, sentences=[], message="m"))
    with caplog.at_level(logging.INFO), make_client(services) as c:
        c.get("/v1/search", params={"q": "SECRET-CLIENT-FACTS"})
        c.post("/v1/judgments/2024_10_108_125/questions", json={"question": "SECRET-QUESTION"})
    # Only the server's own loggers count; the test client's httpx logger prints the URL it requested.
    server_logs = "\n".join(r.getMessage() for r in caplog.records if not r.name.startswith("httpx"))
    assert "SECRET" not in server_logs
    assert '"route": "/v1/search"' in server_logs


def test_unexpected_errors_do_not_leak_details():
    services = FakeServices(judgment=judgment())

    def boom(*_):
        raise RuntimeError("password=hunter2 at /srv/app.py line 3")

    services.search.search = boom
    with TestClient(create_app(Settings(database_url="postgresql://unused"), services),
                    raise_server_exceptions=False) as c:
        response = c.get("/v1/search", params={"q": "a"})
    assert response.status_code == 500
    assert "hunter2" not in response.text and response.json()["error"]["code"] == "internal_error"


def test_new_search_parameters_reach_the_service():
    services = FakeServices(judgment=judgment())
    with make_client(services) as c:
        response = c.get("/v1/search", params=[("q", "bail"), ("judge", "Pardiwala"), ("judge", "Mahadevan"),
                                              ("author", "Oka"), ("outcome", "dismissed"), ("role", "reasoning"),
                                              ("role", "conclusion"), ("date_from", "2025-01-01"),
                                              ("date_to", "2025-03-31")])
    assert response.status_code == 200, response.text
    _, filters, _ = services.last_search
    assert filters.judges == ["Pardiwala", "Mahadevan"] and filters.author == "Oka"
    assert [r.value for r in filters.roles] == ["reasoning", "conclusion"] and filters.outcome.value == "dismissed"
    assert str(filters.date_from) == "2025-01-01"


@pytest.mark.parametrize("params", [
    {"q": "a", "role": "verdict"},
    {"q": "a", "outcome": "won"},
    {"q": "a", "date_from": "31-03-2025"},
    {"q": "a", "date_from": "2025-04-01", "date_to": "2025-03-01"},
])
def test_invalid_new_filters_are_422(client, params):
    response = client.get("/v1/search", params=params)
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_request"


def test_judge_list(client):
    body = client.get("/v1/judges").json()
    assert body == {"judges": [{"name": "J.B. Pardiwala", "judgments": 12}]}
