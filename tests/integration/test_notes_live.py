import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def note(client, judgment_id):
    body = {"items": [{"judgment_id": judgment_id, "label": "2"}, {"judgment_id": judgment_id, "label": "O2-1"}]}
    response = client.post("/v1/notes", json=body)
    assert response.status_code == 201, response.text
    created = response.json()
    yield created
    client.delete(f"/v1/notes/{created['id']}", headers={"X-Note-Token": created["owner_token"]})


def test_create_returns_id_and_owner_token_once(note):
    assert len(note["owner_token"]) >= 40 and note["id"] and note["expires_at"]


def test_recipient_reads_current_corpus_text(client, note, judgment_id):
    body = client.get(f"/v1/notes/{note['id']}")
    assert body.status_code == 200
    items = body.json()["items"]
    assert [i["label"] for i in items] == ["2", "O2-1"]
    assert all(i["judgment"]["id"] == judgment_id for i in items)
    assert items[0]["text"]  # read from the corpus, not from what the sender sent


def test_stored_note_holds_references_only(client, db, note, judgment_id):
    row = db.fetch_one("SELECT items::text AS items FROM shared_notes WHERE id = %s", [note["id"]])
    assert '"judgment_id"' in row["items"] and '"text"' not in row["items"] and "¶" not in row["items"]


def test_missing_paragraph_is_reported_not_guessed(client, judgment_id):
    created = client.post("/v1/notes", json={"items": [{"judgment_id": judgment_id, "label": "9999"}]}).json()
    items = client.get(f"/v1/notes/{created['id']}").json()["items"]
    assert items[0]["text"] is None
    client.delete(f"/v1/notes/{created['id']}", headers={"X-Note-Token": created["owner_token"]})


def test_renew_and_revoke_need_the_owner_token(client, note):
    assert client.post(f"/v1/notes/{note['id']}/renewal", headers={"X-Note-Token": "x" * 30}).status_code == 404
    renewed = client.post(f"/v1/notes/{note['id']}/renewal", headers={"X-Note-Token": note["owner_token"]})
    assert renewed.status_code == 200 and renewed.json()["expires_at"]


def test_revoked_note_shows_withdrawn(client, note):
    assert client.delete(f"/v1/notes/{note['id']}", headers={"X-Note-Token": "x" * 30}).status_code == 404
    assert client.delete(f"/v1/notes/{note['id']}", headers={"X-Note-Token": note["owner_token"]}).status_code == 204
    response = client.get(f"/v1/notes/{note['id']}")
    assert response.status_code == 410 and response.json()["error"]["code"] == "note_withdrawn"


def test_unknown_or_malformed_ids(client):
    assert client.get("/v1/notes/00000000-0000-4000-8000-000000000000").status_code == 404
    assert client.get("/v1/notes/not-a-uuid").status_code == 422


def test_validation(client, judgment_id):
    assert client.post("/v1/notes", json={"items": []}).status_code == 422
    bad_label = {"items": [{"judgment_id": judgment_id, "label": "2; drop"}]}
    assert client.post("/v1/notes", json=bad_label).status_code == 422
    unknown = client.post("/v1/notes", json={"items": [{"judgment_id": "2099_1_1_1", "label": "1"}]})
    assert unknown.status_code == 422
