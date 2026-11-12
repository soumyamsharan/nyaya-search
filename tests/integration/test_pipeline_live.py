import pytest

from nyaya.config import Settings
from nyaya_pipeline import stages

pytestmark = pytest.mark.integration


def test_re_ingestion_keeps_paragraph_ids_labels_text_and_embeddings(db, settings, judgment_id):
    query = "SELECT id, seq, label, text, embedding IS NOT NULL AS embedded FROM paragraphs WHERE judgment_id = %s " \
            "ORDER BY seq"
    before = db.fetch_all(query, [judgment_id])
    report = stages.extract(db, settings, judgment_id, force=True)
    assert report.counts["failed"] == 0
    assert db.fetch_all(query, [judgment_id]) == before


def test_unchanged_judgment_is_skipped(db, settings, judgment_id):
    assert stages.extract(db, settings, judgment_id).counts["unchanged"] == 1


def test_one_corrupt_pdf_is_isolated_and_reported(db, tmp_path):
    settings = Settings(data_dir=tmp_path)
    (tmp_path / "pdf" / "2099").mkdir(parents=True)
    (tmp_path / "pdf" / "2099" / "2099_1_1_2_EN.pdf").write_bytes(b"not a pdf")
    db.execute("INSERT INTO judgments (id, year, title, pdf_url) VALUES ('2099_1_1_2', 2099, 'Corrupt v. Test', "
               "'https://example.invalid') ON CONFLICT (id) DO NOTHING")
    try:
        report = stages.extract(db, settings, "2099_1_1_2", force=True)
        assert report.counts["failed"] == 1 and report.failures[0][0] == "2099_1_1_2"
        row = db.fetch_one("SELECT status, status_reason FROM judgments WHERE id = '2099_1_1_2'")
        assert row["status"] == "failed" and row["status_reason"]
    finally:
        db.execute("DELETE FROM judgments WHERE id = '2099_1_1_2'")


def test_ingest_runs_are_recorded(db):
    stages_seen = {r["stage"] for r in db.fetch_all("SELECT DISTINCT stage FROM ingest_runs")}
    assert {"metadata", "extract"} <= stages_seen


def test_reporter_case_law_cited_is_stored(db):
    assert db.fetch_one("SELECT count(*) AS n FROM front_matter WHERE section = 'case_law_cited'")["n"] > 100
