import pytest

pytestmark = pytest.mark.integration


def search(client, params):
    response = client.get("/v1/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_misspelled_words_get_a_suggestion(client):
    assert search(client, {"q": "tennant evicton arears of rent"})["suggestion"] == "tenant eviction arrears of rent"


def test_misspelled_word_inside_a_phrase(client):
    assert search(client, {"q": '"demand notise" cheque'})["suggestion"] == '"demand notice" cheque'


def test_correct_spelling_has_no_suggestion(client):
    assert search(client, {"q": "tenant eviction arrears of rent"})["suggestion"] is None


def test_citation_query_has_no_suggestion(client):
    assert search(client, {"q": "2024 INSC 874"})["suggestion"] is None


def test_short_query_with_typos_still_finds_tenancy_judgments(client, db):
    body = search(client, {"q": "tennant evicton arears of rent"})
    assert body["results"]
    texts = " ".join(r["matched_paragraph"]["text"].lower() for r in body["results"][:5])
    assert any(word in texts for word in ("tenant", "evict", "rent", "landlord"))


def test_judge_list_has_counts(client):
    judges = client.get("/v1/judges").json()["judges"]
    names = [j["name"] for j in judges]
    assert names == sorted(names) and any("Pardiwala" in n for n in names)
    assert all(j["judgments"] > 0 for j in judges)


def test_misspelled_judge_matches(client):
    results = search(client, {"q": "appeal", "judge": "Pardivala"})["results"]
    assert results and all(any("Pardiwala" in b for b in r["judgment"]["bench"]) for r in results)


def test_short_author_stays_exact(client, db):
    results = search(client, {"q": "appeal", "author": "Oka"})["results"]
    for r in results:
        author = db.fetch_one("SELECT author FROM judgments WHERE id = %s", [r["judgment"]["id"]])["author"]
        assert "oka" in author.lower()
