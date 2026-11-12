import pytest

pytestmark = pytest.mark.integration


def test_statute_index_lists_acts_with_sections(client):
    acts = client.get("/v1/statutes").json()["acts"]
    assert acts and acts == sorted(acts, key=lambda a: -a["judgments"])
    assert all(a["sections"] and all(s["judgments"] > 0 for s in a["sections"]) for a in acts)
    assert all(a["key"] == a["key"].lower() and " " not in a["key"] for a in acts)


def test_section_page_lists_judgments_with_referring_paragraphs(client):
    page = client.get("/v1/statutes/negotiable-instruments-act/sections/138")
    assert page.status_code == 200, page.text
    body = page.json()
    assert body["section"] == "138" and body["judgments"]
    for entry in body["judgments"][:5]:
        assert entry["paragraphs"]
        assert all("138" in p["text"] for p in entry["paragraphs"])


def test_unknown_section_is_404(client):
    response = client.get("/v1/statutes/negotiable-instruments-act/sections/9999")
    assert response.status_code == 404 and response.json()["error"]["code"] == "not_found"


def test_bad_section_format_is_rejected(client):
    assert client.get("/v1/statutes/negotiable-instruments-act/sections/drop-table").status_code == 422


def test_paragraph_carries_statute_links(client, db):
    row = db.fetch_one("SELECT judgment_id FROM judgment_acts WHERE section = '138' LIMIT 1")
    paragraphs = client.get(f"/v1/judgments/{row['judgment_id']}").json()["paragraphs"]
    assert any(p["statutes"] for p in paragraphs)
