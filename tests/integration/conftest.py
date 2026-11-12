"""Integration fixtures: the real API app over the local database, models and LLM (Ollama by default)."""

import pytest
from fastapi.testclient import TestClient

from nyaya.config import Settings
from nyaya.db import Database
from nyaya_api.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(rate_limit="10000/minute")


@pytest.fixture(scope="session")
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture(scope="session")
def db(settings):
    database = Database(settings.database_dsn)
    yield database
    database.close()


@pytest.fixture(scope="session")
def judgment_id(db) -> str:
    """A judgment with numbered paragraphs, reporter headnotes and an INSC citation."""
    row = db.fetch_one(
        """SELECT j.id FROM judgments j
           WHERE j.status = 'ok' AND j.neutral_citation IS NOT NULL
             AND EXISTS (SELECT 1 FROM front_matter f WHERE f.judgment_id = j.id AND f.section = 'headnotes')
             AND NOT EXISTS (SELECT 1 FROM paragraphs p WHERE p.judgment_id = j.id AND p.label_derived)
             AND (SELECT count(*) FROM paragraphs p WHERE p.judgment_id = j.id) BETWEEN 15 AND 40
           ORDER BY j.id LIMIT 1"""
    )
    return row["id"]
