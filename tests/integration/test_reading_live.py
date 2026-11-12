import pytest
from fastapi.testclient import TestClient

from nyaya.config import Settings
from nyaya_api.main import create_app

pytestmark = pytest.mark.integration


def test_judgment_view_has_labelled_paragraphs_front_matter_and_pdf(client, judgment_id):
    body = client.get(f"/v1/judgments/{judgment_id}").json()
    labels = [p["label"] for p in body["paragraphs"]]
    assert labels[:3] == ["1", "2", "3"]
    assert body["numbering_derived"] is False
    assert any(s["section"] == "headnotes" for s in body["reporter_front_matter"])
    assert body["pdf_url"].startswith("https://") and body["pdf_url"].endswith("_EN.pdf")
    assert body["bench"]


def test_derived_numbering_is_flagged(client, db):
    row = db.fetch_one("SELECT judgment_id FROM paragraphs WHERE label_derived LIMIT 1")
    if not row:
        pytest.skip("no judgment with derived numbering in the corpus")
    assert client.get(f"/v1/judgments/{row['judgment_id']}").json()["numbering_derived"] is True


def test_breakdown_lines_cite_real_paragraphs_and_are_cached(client, db, judgment_id):
    db.execute("DELETE FROM breakdowns WHERE judgment_id = %s", [judgment_id])
    first = client.get(f"/v1/judgments/{judgment_id}/breakdown")
    assert first.status_code == 200, first.text
    body = first.json()
    labels = {p["label"] for p in client.get(f"/v1/judgments/{judgment_id}").json()["paragraphs"]}
    sentences = [s for key in ("facts", "issues", "held", "ratio") for s in body[key]]
    assert sentences and body["machine_generated"]
    assert all(s["paragraphs"] and {p["label"] for p in s["paragraphs"]} <= labels for s in sentences)

    calls_before = db.fetch_one("SELECT count(*) AS n FROM llm_calls")["n"]
    assert client.get(f"/v1/judgments/{judgment_id}/breakdown").json() == body
    assert db.fetch_one("SELECT count(*) AS n FROM llm_calls")["n"] == calls_before  # served from cache


def test_answerable_question_cites_paragraphs(client, db, judgment_id):
    question = "What was the final outcome of the appeal and what did the court direct?"
    response = client.post(f"/v1/judgments/{judgment_id}/questions", json={"question": question})
    assert response.status_code == 200, response.text
    body = response.json()
    if body["answered"]:
        assert all(s["paragraphs"] for s in body["sentences"])
    else:  # grounding may refuse; it must then say so rather than return an empty answer
        assert body["message"]
    assert not db.fetch_one("SELECT 1 AS hit FROM llm_calls WHERE purpose ILIKE %s OR prompt_version ILIKE %s",
                            ["%final outcome%", "%final outcome%"])


def test_unrelated_question_is_refused(client, judgment_id):
    body = client.post(f"/v1/judgments/{judgment_id}/questions",
                       json={"question": "What is the boiling point of mercury in Kelvin?"}).json()
    assert body["answered"] is False and body["message"]


def test_citation_graph_shape_and_cited_by(client, db):
    row = db.fetch_one("SELECT cited_judgment_id FROM citations WHERE cited_judgment_id IS NOT NULL "
                       "GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")
    if not row:
        pytest.skip("no resolved citations in the corpus")
    target = row["cited_judgment_id"]
    graph = client.get(f"/v1/judgments/{target}/citations").json()
    assert graph["cited_by"]
    link = graph["cited_by"][0]
    assert link["paragraph"]["label"] and link["paragraph_text"]
    result = client.get("/v1/search", params={"q": db.fetch_one(
        "SELECT neutral_citation FROM judgments WHERE id=%s", [target])["neutral_citation"]}).json()["results"][0]
    assert result["judgment"]["cited_by_count"] >= 1


def test_unresolved_citations_are_listed_as_text(client, db):
    row = db.fetch_one("SELECT citing_judgment_id FROM citations WHERE cited_judgment_id IS NULL LIMIT 1")
    graph = client.get(f"/v1/judgments/{row['citing_judgment_id']}/citations").json()
    assert graph["unresolved"] and graph["unresolved"][0]["raw"]


def test_overruling_language_is_evidence_not_verdict(client, db):
    row = db.fetch_one("SELECT cited_judgment_id FROM citations WHERE overruling_language "
                       "AND cited_judgment_id IS NOT NULL LIMIT 1")
    if not row:
        pytest.skip("no resolved citation with overruling language in the corpus")
    graph = client.get(f"/v1/judgments/{row['cited_judgment_id']}/citations").json()
    assert graph["overruling_evidence"] and graph["overruling_evidence"][0]["paragraph_text"]


def test_daily_cap_blocks_ai_but_search_and_cache_still_work(settings, client, judgment_id):
    client.get(f"/v1/judgments/{judgment_id}/breakdown")  # ensure cached
    capped = Settings(rate_limit="10000/minute", llm_daily_cap=0)
    with TestClient(create_app(capped)) as c:
        busy = c.post(f"/v1/judgments/{judgment_id}/questions", json={"question": "What was held?"})
        assert busy.status_code == 503 and busy.json()["error"]["code"] == "llm_busy"
        assert c.get("/v1/search", params={"q": "bail"}).status_code == 200
        assert c.get(f"/v1/judgments/{judgment_id}/breakdown").status_code == 200  # cached copy
