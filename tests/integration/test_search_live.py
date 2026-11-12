import statistics
import time

import pytest

pytestmark = pytest.mark.integration

FACT_PATTERN = "cheque dishonoured, statutory demand notice not received by the drawer, complaint under section 138"


def search(client, **params):
    response = client.get("/v1/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_fact_pattern_search_returns_distinct_judgments_with_matched_paragraph(client):
    body = search(client, q=FACT_PATTERN)
    ids = [r["judgment"]["id"] for r in body["results"]]
    assert 0 < len(ids) <= 10 and len(set(ids)) == len(ids)
    top = body["results"][0]
    assert top["matched_paragraph"]["label"] and top["matched_paragraph"]["text"]
    assert "138" in " ".join(r["matched_paragraph"]["text"] for r in body["results"][:3])


def test_phrase_search_requires_the_exact_phrase(client, db):
    body = search(client, q='"demand notice" cheque')
    assert body["results"]
    for result in body["results"]:
        texts = db.fetch_all("SELECT text FROM paragraphs WHERE judgment_id = %s", [result["judgment"]["id"]])
        assert any("demand notice" in t["text"].lower() for t in texts)


def test_year_filter(client):
    body = search(client, q="bail conditions", year_from=2025, year_to=2025)
    assert body["results"]
    assert all(r["judgment"]["decision_date"].startswith("2025") for r in body["results"])


def test_act_and_section_filter(client, db):
    body = search(client, q="dishonour of cheque", act="Negotiable Instruments Act", section="138")
    assert body["results"]
    for r in body["results"]:
        rows = db.fetch_all("SELECT act_norm, section FROM judgment_acts WHERE judgment_id = %s",
                            [r["judgment"]["id"]])
        assert any("negotiable instruments" in a["act_norm"] and a["section"] == "138" for a in rows)


def test_judge_filter(client, db):
    judge = db.fetch_one("SELECT b FROM judgments, unnest(bench) b WHERE status='ok' GROUP BY b "
                         "ORDER BY count(*) DESC LIMIT 1")["b"]
    body = search(client, q="appeal against conviction", judge=judge.split()[-1])
    assert body["results"]
    assert all(any(judge.split()[-1] in name for name in r["judgment"]["bench"]) for r in body["results"])


def test_search_by_known_citation_returns_only_that_judgment(client, db, judgment_id):
    citation = db.fetch_one("SELECT neutral_citation FROM judgments WHERE id = %s", [judgment_id])["neutral_citation"]
    body = search(client, q=citation)
    assert body["query_type"] == "citation"
    assert [r["judgment"]["id"] for r in body["results"]] == [judgment_id]


def test_citation_not_in_corpus(client):
    body = search(client, q="(1961) 1 SCC 1")
    assert body["results"] == [] and "not in the corpus" in body["message"]


def test_off_topic_query_says_nothing_relevant(client):
    body = search(client, q="sourdough bread recipe with rye flour and a long cold fermentation")
    assert body["results"] == []
    assert body["message"] == "No relevant judgments found."


def test_search_p95_latency_under_3_seconds(client):
    queries = [FACT_PATTERN, "tenant eviction arrears of rent", "anticipatory bail economic offence",
               "motor accident compensation multiplier", "termination of service without inquiry",
               "land acquisition compensation market value", "dowry death section 304B presumption",
               "arbitral award set aside public policy", "NDPS commercial quantity bail",
               "specific performance readiness"]
    timings = []
    for q in queries:
        started = time.monotonic()
        search(client, q=q)
        timings.append(time.monotonic() - started)
    p95 = statistics.quantiles(timings, n=20)[-1]
    print(f"search p95 = {p95:.2f}s")
    assert p95 < 3.0


def test_search_text_is_not_stored(client, db):
    marker = "zqxjmarker unusual client facts"
    search(client, q=marker)
    for table, column in [("llm_calls", "purpose"), ("ingest_runs", "counts::text"), ("breakdowns", "content::text")]:
        assert not db.fetch_one(f"SELECT 1 AS hit FROM {table} WHERE {column} ILIKE %s", [f"%{marker}%"])
