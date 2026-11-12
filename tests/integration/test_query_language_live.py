import re

import pytest

pytestmark = pytest.mark.integration


def search(client, params):
    response = client.get("/v1/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()["results"]


def matched(result) -> str:
    return result["matched_paragraph"]["text"].lower()


def test_and_requires_both_terms(client):
    results = search(client, {"q": "cheque AND dishonour"})
    assert results
    assert all("cheque" in matched(r) and re.search(r"\bdishonour", matched(r)) for r in results)


def test_not_excludes_a_term(client):
    results = search(client, {"q": "bail NOT anticipatory"})
    assert results and all("anticipatory" not in matched(r) for r in results)


def test_not_excludes_a_phrase(client):
    results = search(client, {"q": 'eviction NOT "bona fide requirement"'})
    assert results and all("bona fide requirement" not in matched(r) for r in results)


def test_lower_case_not_is_a_word(client):
    assert search(client, {"q": "notice not received"})


def test_only_excluded_terms_is_rejected(client):
    response = client.get("/v1/search", params={"q": "NOT bail"})
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_request"


def test_search_within_reasoning_and_conclusion(client):
    results = search(client, [("q", "demand notice cheque"), ("role", "reasoning"), ("role", "conclusion")])
    assert results and all(r["matched_paragraph"]["role"] in ("reasoning", "conclusion") for r in results)


def test_date_range(client):
    results = search(client, {"q": "bail", "date_from": "2025-01-01", "date_to": "2025-03-31"})
    assert results and all("2025-01-01" <= r["judgment"]["decision_date"] <= "2025-03-31" for r in results)


def test_author_filter(client, db):
    results = search(client, {"q": "appeal", "author": "Pardiwala"})
    assert results
    for r in results:
        author = db.fetch_one("SELECT author FROM judgments WHERE id = %s", [r["judgment"]["id"]])["author"]
        assert "pardiwala" in author.lower()


def test_bench_with_two_judges(client):
    results = search(client, [("q", "appeal"), ("judge", "Pardiwala"), ("judge", "Mahadevan")])
    assert results
    for r in results:
        bench = " ".join(r["judgment"]["bench"]).lower()
        assert "pardiwala" in bench and "mahadevan" in bench


def test_outcome_dismissed(client, db):
    results = search(client, {"q": "appeal", "outcome": "dismissed"})
    assert results
    for r in results:
        disposal = db.fetch_one("SELECT disposal_nature FROM judgments WHERE id = %s", [r["judgment"]["id"]])
        assert disposal["disposal_nature"] in ("Dismissed", "Rejected")


def test_judgment_paragraphs_carry_roles(client, judgment_id):
    paragraphs = client.get(f"/v1/judgments/{judgment_id}").json()["paragraphs"]
    assert all(p["role"] for p in paragraphs)
