"""Ingestion CLI: `pipeline <stage>`. Each stage prints and saves its report."""

import logging
from typing import Annotated

import typer

from nyaya.config import get_settings
from nyaya.db import Database
from nyaya.ml import build_embedder
from nyaya_pipeline import stages
from nyaya_pipeline.report import RunReport

app = typer.Typer(add_completion=False, help="Nyaya Search ingestion pipeline")
Years = Annotated[list[int] | None, typer.Option("--year", help="Repeatable; defaults to INGEST_YEARS")]


def _db() -> Database:
    return Database(get_settings().database_dsn)


def _finish(db: Database, report: RunReport) -> None:
    typer.echo(report.summary())
    if report.save(db, get_settings().max_failure_share) != "ok":
        raise typer.Exit(code=1)


@app.callback()
def _configure() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@app.command()
def migrate() -> None:
    """Apply database migrations."""
    applied = _db().migrate()
    typer.echo(f"applied: {applied or 'nothing'}")


@app.command()
def sync(year: Years = None) -> None:
    """Download PDFs and metadata, then load metadata into the database."""
    settings = get_settings()
    years = year or settings.ingest_years
    stages.sync(settings, years)
    db = _db()
    _finish(db, stages.load_metadata(db, settings, years))


@app.command()
def extract(
    judgment: Annotated[str | None, typer.Option(help="Only this judgment id")] = None,
    force: Annotated[bool, typer.Option(help="Re-parse even if unchanged")] = False,
) -> None:
    """Extract text, front matter and paragraphs from PDFs."""
    db = _db()
    _finish(db, stages.extract(db, get_settings(), judgment, force))


@app.command()
def index() -> None:
    """Embed paragraphs that are not embedded yet."""
    db = _db()
    _finish(db, stages.index(db, build_embedder(get_settings())))


@app.command()
def citations() -> None:
    """Rebuild citation aliases and citation edges."""
    db = _db()
    _finish(db, stages.citations(db))


@app.command(name="roles")
def roles_stage() -> None:
    """Label every paragraph with its role (facts, arguments, reasoning, ...)."""
    db = _db()
    _finish(db, stages.roles(db))


@app.command(name="vocabulary")
def vocabulary_stage() -> None:
    """Rebuild the corpus word list used for spelling suggestions."""
    db = _db()
    _finish(db, stages.vocabulary(db))


@app.command(name="all")
def run_all(year: Years = None) -> None:
    """migrate -> sync -> extract -> roles -> vocabulary -> index -> citations."""
    migrate()
    sync(year)
    extract()
    roles_stage()
    vocabulary_stage()
    index()
    citations()
