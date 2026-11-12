"""Ingestion stages. Each is idempotent, re-runnable for one judgment or all, and isolates failures."""

import hashlib
import logging
import subprocess
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq

from nyaya.config import Settings
from nyaya.db import Database
from nyaya.ml import Embedder
from nyaya.parsing.pdf import extract_pdf
from nyaya.parsing.scr import EXTRACTOR_VERSION, ParsedJudgment, parse_judgment
from nyaya.roles import assign_roles
from nyaya.text import (
    cites_cases,
    clean_case_title,
    extract_citations,
    find_section_references,
    has_overruling_language,
    normalize_act,
    normalize_citation,
)
from nyaya_pipeline.report import RunReport

log = logging.getLogger(__name__)


class Paths:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.data_dir

    def pdf_dir(self, year: int) -> Path:
        return self.root / "pdf" / str(year)

    def pdf(self, year: int, judgment_id: str) -> Path:
        return self.pdf_dir(year) / f"{judgment_id}_EN.pdf"

    def metadata(self, year: int) -> Path:
        return self.root / "metadata" / f"{year}.parquet"


def _aws_s3(*args: str) -> None:
    subprocess.run(["aws", "s3", *args, "--no-sign-request", "--only-show-errors"], check=True)


def sync(settings: Settings, years: list[int]) -> None:
    """Incrementally download PDFs and metadata for the given years."""
    paths = Paths(settings)
    bucket = f"s3://{settings.dataset_bucket}"
    for year in years:
        paths.pdf_dir(year).mkdir(parents=True, exist_ok=True)
        paths.metadata(year).parent.mkdir(parents=True, exist_ok=True)
        _aws_s3("sync", f"{bucket}/data/pdf/year={year}/english/", str(paths.pdf_dir(year)))
        if not paths.metadata(year).exists():
            _aws_s3("cp", f"{bucket}/metadata/parquet/year={year}/metadata.parquet", str(paths.metadata(year)))


def _parse_date(value: str | None) -> date | None:
    try:
        return datetime.strptime(value or "", "%d-%m-%Y").date()
    except ValueError:
        return None


def _citation_text(value: str | None) -> str | None:
    """Keep a metadata citation only if it parses as one."""
    return value.strip() if value and normalize_citation(value) else None


def load_metadata(db: Database, settings: Settings, years: list[int]) -> RunReport:
    """Upsert judgment metadata for every downloaded English PDF."""
    report = RunReport("metadata")
    paths = Paths(settings)
    for year in years:
        seen_citations: set[str] = set()
        for row in pq.read_table(paths.metadata(year)).to_pylist():
            judgment_id = row["path"]
            if not paths.pdf(year, judgment_id).exists():
                report.counts["no_english_pdf"] += 1
                continue
            neutral = _citation_text(row.get("case_id"))
            if neutral and neutral in seen_citations:
                report.counts["duplicates"] += 1
                continue
            if neutral:
                seen_citations.add(neutral)
            report.counts["processed"] += 1
            db.execute(
                """INSERT INTO judgments (id, year, title, petitioner, respondent, decision_date,
                                          neutral_citation, scr_citation, disposal_nature, pdf_url)
                   VALUES (%(id)s, %(year)s, %(title)s, %(pet)s, %(res)s, %(date)s, %(nc)s, %(scr)s,
                           %(disp)s, %(url)s)
                   ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, petitioner = EXCLUDED.petitioner,
                       respondent = EXCLUDED.respondent, decision_date = EXCLUDED.decision_date,
                       neutral_citation = EXCLUDED.neutral_citation, scr_citation = EXCLUDED.scr_citation,
                       disposal_nature = EXCLUDED.disposal_nature, pdf_url = EXCLUDED.pdf_url""",
                {
                    "id": judgment_id,
                    "year": year,
                    "title": clean_case_title(row.get("title") or judgment_id),
                    "pet": row.get("petitioner"),
                    "res": row.get("respondent"),
                    "date": _parse_date(row.get("decision_date")),
                    "nc": neutral,
                    "scr": _citation_text(row.get("citation")),
                    "disp": row.get("disposal_nature"),
                    "url": f"https://{settings.dataset_bucket}.s3.amazonaws.com/data/pdf/year={year}"
                    f"/english/{judgment_id}_EN.pdf",
                },
            )
    return report


def _acts(parsed: ParsedJudgment) -> set[tuple[str, str, str | None]]:
    """(act_norm, act_display, section) rows from the reporter's list of Acts and body references."""
    rows: set[tuple[str, str, str | None]] = set()
    for name in parsed.front_matter.get("acts", "").replace(";", ".").split("."):
        name = name.strip()
        if len(name) > 3 and not name.isdigit():
            rows.add((normalize_act(name), name, None))
    for paragraph in parsed.paragraphs:
        for act, section in find_section_references(paragraph.text):
            rows.add((normalize_act(act), act, section))
    return rows


def _save_parsed(db: Database, judgment_id: str, parsed: ParsedJudgment, sha: str) -> None:
    new_rows = [(p.seq, p.opinion_idx, p.label, p.label_derived, p.text) for p in parsed.paragraphs]
    with db.connection() as conn, conn.transaction():
        old_rows = conn.execute(
            "SELECT seq, opinion_idx, label, label_derived, text FROM paragraphs WHERE judgment_id = %s ORDER BY seq",
            [judgment_id],
        ).fetchall()
        # Identical paragraphs are left untouched so their ids and embeddings survive a re-run.
        if [tuple(r.values()) for r in old_rows] != new_rows:
            conn.execute("DELETE FROM paragraphs WHERE judgment_id = %s", [judgment_id])
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO paragraphs (judgment_id, seq, opinion_idx, label, label_derived, text)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    [(judgment_id, *row) for row in new_rows],
                )
        conn.execute("DELETE FROM front_matter WHERE judgment_id = %s", [judgment_id])
        conn.execute("DELETE FROM judgment_acts WHERE judgment_id = %s", [judgment_id])
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO front_matter (judgment_id, section, text) VALUES (%s, %s, %s)",
                [(judgment_id, k, v) for k, v in parsed.front_matter.items()],
            )
            cur.executemany(
                """INSERT INTO judgment_acts (judgment_id, act_norm, act_display, section)
                   VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                [(judgment_id, *row) for row in _acts(parsed)],
            )
        conn.execute(
            """UPDATE judgments SET bench = %s, author = %s, case_name = %s, status = 'ok', status_reason = NULL,
                   extractor_version = %s, pdf_sha256 = %s, updated_at = now() WHERE id = %s""",
            [parsed.bench, parsed.author, parsed.case_name, EXTRACTOR_VERSION, sha, judgment_id],
        )


def _set_status(db: Database, judgment_id: str, status: str, reason: str | None, sha: str | None) -> None:
    db.execute(
        """UPDATE judgments SET status = %s, status_reason = %s, extractor_version = %s, pdf_sha256 = %s,
               updated_at = now() WHERE id = %s""",
        [status, reason, EXTRACTOR_VERSION, sha, judgment_id],
    )


def extract(db: Database, settings: Settings, judgment_id: str | None = None, force: bool = False) -> RunReport:
    """Parse PDFs whose content or extractor version changed (or all with force)."""
    report = RunReport("extract")
    paths = Paths(settings)
    rows = db.fetch_all(
        """SELECT id, year, pdf_sha256, extractor_version, status FROM judgments
           WHERE (%(id)s::text IS NULL OR id = %(id)s) ORDER BY id""",
        {"id": judgment_id},
    )
    for row in rows:
        report.counts["processed"] += 1
        try:
            data = paths.pdf(row["year"], row["id"]).read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            unchanged = row["pdf_sha256"] == sha and row["extractor_version"] == EXTRACTOR_VERSION
            if unchanged and row["status"] != "pending" and not force:
                report.counts["processed"] -= 1
                report.counts["unchanged"] += 1
                continue
            text = extract_pdf(data)
            if text.looks_scanned:
                _set_status(db, row["id"], "scanned", "too little extractable text", sha)
                report.counts["scanned"] += 1
                continue
            parsed = parse_judgment(text.lines)
            if not parsed.paragraphs:
                raise ValueError("no paragraphs found")
            report.counts["empty_paragraphs"] += sum(1 for p in parsed.paragraphs if not p.text.strip())
            report.counts["derived_numbering"] += int(parsed.paragraphs[0].label_derived)
            report.counts["paragraphs"] += len(parsed.paragraphs)
            _save_parsed(db, row["id"], parsed, sha)
        except Exception as exc:  # isolate one bad PDF from the batch
            log.warning("extract failed for %s: %s", row["id"], exc)
            report.fail(row["id"], f"{type(exc).__name__}: {exc}")
            _set_status(db, row["id"], "failed", f"{type(exc).__name__}: {exc}"[:500], None)
    return report


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


def index(db: Database, embedder: Embedder, batch_size: int = 512) -> RunReport:
    """Embed paragraphs that have no embedding yet. Large fetches let the encoder sort by length (less padding)."""
    report = RunReport("index")
    while True:
        rows = db.fetch_all(
            """SELECT p.id, p.text FROM paragraphs p JOIN judgments j ON j.id = p.judgment_id
               WHERE p.embedding IS NULL AND j.status = 'ok' ORDER BY p.id LIMIT %s""",
            [batch_size],
        )
        if not rows:
            return report
        vectors = embedder.embed([r["text"] for r in rows])
        with db.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                "UPDATE paragraphs SET embedding = %s::halfvec WHERE id = %s",
                [(_vector_literal(v.tolist()), r["id"]) for r, v in zip(rows, vectors, strict=True)],
            )
        report.counts["processed"] += len(rows)
        log.info("embedded %s paragraphs", report.counts["processed"])


class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, items: list[str]) -> None:
        for other in items[1:]:
            self._parent[self.find(other)] = self.find(items[0])

    def groups(self) -> list[set[str]]:
        members: dict[str, set[str]] = {}
        for item in list(self._parent):
            members.setdefault(self.find(item), set()).add(item)
        return list(members.values())


def build_aliases(own: dict[str, str], case_law_entries: list[str]) -> dict[str, str]:
    """Map every known citation to a judgment id.

    own: citation_norm -> judgment id (each judgment's own citations).
    case_law_entries: reporter 'case law cited' entries; citations within one entry are the same case.
    A group linked to more than one judgment is ambiguous, so only the judgments' own citations map.
    """
    groups = _UnionFind()
    for norm in own:
        groups.find(norm)
    for entry in case_law_entries:
        norms = [c.norm for c in extract_citations(entry)]
        if norms:
            groups.union(norms)
    aliases = dict(own)
    for group in groups.groups():
        judgment_ids = {own[n] for n in group if n in own}
        if len(judgment_ids) == 1:
            target = judgment_ids.pop()
            aliases.update(dict.fromkeys(group, target))
    return aliases


def citations(db: Database) -> RunReport:
    """Rebuild citation aliases and paragraph-level citation edges."""
    report = RunReport("citations")
    own: dict[str, str] = {}
    for row in db.fetch_all("SELECT id, neutral_citation, scr_citation FROM judgments WHERE status = 'ok'"):
        for value in (row["neutral_citation"], row["scr_citation"]):
            norm = normalize_citation(value) if value else None
            if norm:
                own[norm] = row["id"]
    entries = [
        entry
        for row in db.fetch_all("SELECT text FROM front_matter WHERE section = 'case_law_cited'")
        for entry in row["text"].split(";")
    ]
    aliases = build_aliases(own, entries)

    edges = []
    flags = []
    for p in db.fetch_all(
        """SELECT p.judgment_id, p.seq, p.text FROM paragraphs p JOIN judgments j ON j.id = p.judgment_id
           WHERE j.status = 'ok'"""
    ):
        flags.append((cites_cases(p["text"]), p["judgment_id"], p["seq"]))
        overruling = has_overruling_language(p["text"])
        for c in extract_citations(p["text"]):
            target = aliases.get(c.norm)
            if target == p["judgment_id"]:
                continue
            edges.append((p["judgment_id"], p["seq"], c.raw, c.norm, target, overruling))
            report.counts["resolved" if target else "unresolved"] += 1
    report.counts["processed"] = len(edges)
    report.counts["aliases"] = len(aliases)

    with db.connection() as conn, conn.transaction():
        conn.execute("DELETE FROM citations")
        conn.execute("DELETE FROM citation_aliases")
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE paragraphs SET cites_cases = %s WHERE judgment_id = %s AND seq = %s", flags
            )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO citation_aliases (citation_norm, judgment_id) VALUES (%s, %s)", list(aliases.items())
            )
            cur.executemany(
                """INSERT INTO citations (citing_judgment_id, citing_seq, raw, citation_norm, cited_judgment_id,
                                          overruling_language) VALUES (%s, %s, %s, %s, %s, %s)""",
                edges,
            )
    return report


def roles(db: Database) -> RunReport:
    """Label every paragraph with its role; only changed labels are written."""
    report = RunReport("roles")
    rows = db.fetch_all(
        """SELECT p.id, p.judgment_id, p.text, p.role FROM paragraphs p JOIN judgments j ON j.id = p.judgment_id
           WHERE j.status = 'ok' ORDER BY p.judgment_id, p.seq"""
    )
    changes: list[tuple[str, int]] = []
    by_judgment: dict[str, list[dict]] = {}
    for row in rows:
        by_judgment.setdefault(row["judgment_id"], []).append(row)
    for paragraphs in by_judgment.values():
        for row, role in zip(paragraphs, assign_roles([p["text"] for p in paragraphs]), strict=True):
            report.counts[role.value] += 1
            if row["role"] != role.value:
                changes.append((role.value, row["id"]))
    with db.connection() as conn, conn.cursor() as cur:
        cur.executemany("UPDATE paragraphs SET role = %s WHERE id = %s", changes)
    report.counts["processed"] = len(rows)
    report.counts["changed"] = len(changes)
    return report


def vocabulary(db: Database) -> RunReport:
    """Rebuild the corpus word list (lower-case words of 3-30 letters seen at least twice) for spelling help."""
    report = RunReport("vocabulary")
    with db.connection() as conn, conn.transaction():
        conn.execute("DELETE FROM vocabulary")
        conn.execute(
            r"""INSERT INTO vocabulary (word, freq)
                SELECT w, count(*) FROM paragraphs p JOIN judgments j ON j.id = p.judgment_id,
                     regexp_split_to_table(lower(p.text), '[^a-z]+') AS w
                WHERE j.status = 'ok' AND length(w) BETWEEN 3 AND 30
                GROUP BY w HAVING count(*) >= 2"""
        )
        report.counts["processed"] = conn.execute("SELECT count(*) AS n FROM vocabulary").fetchone()["n"]
    return report
