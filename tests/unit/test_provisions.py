from nyaya import provisions


def test_description_is_none_until_written(monkeypatch):
    monkeypatch.setattr(provisions, "_descriptions", lambda: {"penal-code": {"description": None}})
    assert provisions.description_for("penal-code") is None
    assert provisions.description_for("unknown-act") is None


def test_written_description_is_returned(monkeypatch):
    monkeypatch.setattr(provisions, "_descriptions", lambda: {"penal-code": {"description": "Defines offences."}})
    assert provisions.description_for("penal-code") == "Defines offences."
