"""Repositories: the only place that knows table layouts. Each returns domain models or plain rows."""

import json
import re
from collections.abc import Iterable
from datetime import date

from nyaya.db import Database
from nyaya.domain import (
    CitationGraph,
    CitationLink,
    CitationRef,
    FrontMatterSection,
    JudgeCount,
    Judgment,
    JudgmentSummary,
    Paragraph,
    ParagraphRef,
    SectionCount,
    StatuteIndex,
    StatuteJudgment,
    StatuteParagraph,
    StatuteRef,
    StatuteSectionPage,
    StatuteSummary,
    UnresolvedCitation,
)
from nyaya.parsing.scr import SECTION_TITLES
from nyaya.text import find_statute_references

_SUMMARY_COLUMNS = """
    j.id, coalesce(j.case_name, j.title) AS title, j.decision_date, j.bench,
    coalesce(j.neutral_citation, j.scr_citation) AS citation,
    (SELECT count(DISTINCT c.citing_judgment_id) FROM citations c WHERE c.cited_judgment_id = j.id)
        AS cited_by_count
"""


def _summary(row: dict) -> JudgmentSummary:
    return JudgmentSummary(
        id=row["id"],
        title=row["title"],
        decision_date=row["decision_date"],
        bench=row["bench"] or [],
        citation=row["citation"],
        cited_by_count=row["cited_by_count"],
    )


class JudgmentRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def summaries(self, ids: Iterable[str]) -> dict[str, JudgmentSummary]:
        ids = list(ids)
        if not ids:
            return {}
        rows = self._db.fetch_all(f"SELECT {_SUMMARY_COLUMNS} FROM judgments j WHERE j.id = ANY(%s)", [ids])
        return {row["id"]: _summary(row) for row in rows}

    def paragraphs_by_ids(self, paragraph_ids: Iterable[int]) -> dict[int, tuple[str, Paragraph]]:
        """paragraph id -> (judgment id, paragraph)."""
        rows = self._db.fetch_all(
            "SELECT id, judgment_id, seq, label, label_derived, text, role FROM paragraphs WHERE id = ANY(%s)",
            [list(paragraph_ids)],
        )
        return {
            r["id"]: (
                r["judgment_id"],
                Paragraph(seq=r["seq"], label=r["label"], text=r["text"], label_derived=r["label_derived"],
                          role=r["role"]),
            )
            for r in rows
        }

    def paragraphs(self, judgment_id: str) -> list[Paragraph]:
        rows = self._db.fetch_all(
            "SELECT seq, label, label_derived, text, role, cites_cases FROM paragraphs "
            "WHERE judgment_id = %s ORDER BY seq",
            [judgment_id],
        )
        paragraphs = [Paragraph(**r) for r in rows]
        for paragraph in paragraphs:
            paragraph.statutes = [
                StatuteRef(raw=m.raw, key=m.key, name=m.name, section=m.section)
                for m in find_statute_references(paragraph.text)
            ]
        references = self._db.fetch_all(
            """SELECT c.citing_seq, c.raw, c.cited_judgment_id, coalesce(j.case_name, j.title) AS title,
                      coalesce(j.neutral_citation, j.scr_citation) AS citation
               FROM citations c LEFT JOIN judgments j ON j.id = c.cited_judgment_id
               WHERE c.citing_judgment_id = %s ORDER BY c.citing_seq, c.id""",
            [judgment_id],
        )
        by_seq: dict[int, list[CitationRef]] = {}
        for ref in references:
            by_seq.setdefault(ref["citing_seq"], []).append(
                CitationRef(raw=ref["raw"], judgment_id=ref["cited_judgment_id"], title=ref["title"],
                            citation=ref["citation"])
            )
        for paragraph in paragraphs:
            paragraph.references = by_seq.get(paragraph.seq, [])
        return paragraphs

    def front_matter(self, judgment_id: str) -> dict[str, str]:
        rows = self._db.fetch_all(
            "SELECT section, text FROM front_matter WHERE judgment_id = %s", [judgment_id]
        )
        return {r["section"]: r["text"] for r in rows}

    def get(self, judgment_id: str) -> Judgment | None:
        row = self._db.fetch_one(
            f"""SELECT {_SUMMARY_COLUMNS}, j.author, j.neutral_citation, j.scr_citation, j.disposal_nature,
                       j.pdf_url
                FROM judgments j WHERE j.id = %s AND j.status = 'ok'""",
            [judgment_id],
        )
        if row is None:
            return None
        paragraphs = self.paragraphs(judgment_id)
        front = self.front_matter(judgment_id)
        acts = self._db.fetch_all(
            "SELECT DISTINCT act_display FROM judgment_acts WHERE judgment_id = %s AND section IS NULL "
            "ORDER BY act_display",
            [judgment_id],
        )
        return Judgment(
            **_summary(row).model_dump(),
            author=row["author"],
            neutral_citation=row["neutral_citation"],
            scr_citation=row["scr_citation"],
            disposal_nature=row["disposal_nature"],
            pdf_url=row["pdf_url"],
            acts=[a["act_display"] for a in acts],
            reporter_front_matter=[
                FrontMatterSection(section=key, title=title, text=front[key])
                for key, title in SECTION_TITLES.items()
                if key in front
            ],
            paragraphs=paragraphs,
            numbering_derived=any(p.label_derived for p in paragraphs),
        )

    def judges(self) -> list[JudgeCount]:
        # The dataset spells names inconsistently ("J.B. Pardiwala", "J B Pardiwala"): group by letters only and
        # show the most common spelling.
        rows = self._db.fetch_all(
            """SELECT name, judgments FROM (
                   SELECT mode() WITHIN GROUP (ORDER BY b) AS name, count(*) AS judgments
                   FROM judgments j, unnest(j.bench) b
                   WHERE j.status = 'ok'
                   GROUP BY regexp_replace(lower(b), '[^a-z]', '', 'g')
               ) names ORDER BY name COLLATE "C" """
        )
        return [JudgeCount(**r) for r in rows]

    def exists(self, judgment_id: str) -> bool:
        return self._db.fetch_one(
            "SELECT 1 AS ok FROM judgments WHERE id = %s AND status = 'ok'", [judgment_id]
        ) is not None


class CitationRepository:
    def __init__(self, db: Database, judgments: JudgmentRepository) -> None:
        self._db = db
        self._judgments = judgments

    def resolve(self, citation_norm: str) -> str | None:
        row = self._db.fetch_one(
            """SELECT a.judgment_id FROM citation_aliases a JOIN judgments j ON j.id = a.judgment_id
               WHERE a.citation_norm = %s AND j.status = 'ok'""",
            [citation_norm],
        )
        return row["judgment_id"] if row else None

    def graph(self, judgment_id: str) -> CitationGraph:
        rows = self._db.fetch_all(
            """SELECT c.citing_judgment_id, c.citing_seq, c.raw, c.cited_judgment_id, c.overruling_language,
                      p.label, p.text
               FROM citations c
               JOIN paragraphs p ON p.judgment_id = c.citing_judgment_id AND p.seq = c.citing_seq
               WHERE c.citing_judgment_id = %(id)s OR c.cited_judgment_id = %(id)s
               ORDER BY c.citing_judgment_id, c.citing_seq""",
            {"id": judgment_id},
        )
        other_ids = {r["cited_judgment_id"] for r in rows if r["citing_judgment_id"] == judgment_id}
        other_ids |= {r["citing_judgment_id"] for r in rows if r["cited_judgment_id"] == judgment_id}
        summaries = self._judgments.summaries(i for i in other_ids if i)

        cites: dict[str, CitationLink] = {}
        cited_by: dict[tuple[str, int], CitationLink] = {}
        unresolved: list[UnresolvedCitation] = []
        for r in rows:
            ref = ParagraphRef(seq=r["citing_seq"], label=r["label"])
            if r["citing_judgment_id"] == judgment_id:
                target = r["cited_judgment_id"]
                if target and target in summaries:
                    cites.setdefault(target, CitationLink(judgment=summaries[target], paragraph=ref))
                elif not target:
                    unresolved.append(UnresolvedCitation(raw=r["raw"], paragraph=ref))
            elif r["citing_judgment_id"] in summaries:
                key = (r["citing_judgment_id"], r["citing_seq"])
                cited_by.setdefault(
                    key,
                    CitationLink(
                        judgment=summaries[r["citing_judgment_id"]],
                        paragraph=ref,
                        overruling_language=r["overruling_language"],
                        paragraph_text=r["text"],
                    ),
                )
        evidence = [link for link in cited_by.values() if link.overruling_language]
        return CitationGraph(
            cites=list(cites.values()),
            cited_by=list(cited_by.values()),
            unresolved=unresolved,
            overruling_evidence=evidence,
        )


class BreakdownCache:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, judgment_id: str, prompt_version: str, model: str) -> dict | None:
        row = self._db.fetch_one(
            "SELECT content FROM breakdowns WHERE judgment_id = %s AND prompt_version = %s AND model = %s",
            [judgment_id, prompt_version, model],
        )
        return row["content"] if row else None

    def latest(self, judgment_id: str, prompt_version: str) -> dict | None:
        row = self._db.fetch_one(
            "SELECT content FROM breakdowns WHERE judgment_id = %s AND prompt_version = %s "
            "ORDER BY created_at DESC LIMIT 1",
            [judgment_id, prompt_version],
        )
        return row["content"] if row else None

    def put(self, judgment_id: str, prompt_version: str, model: str, content: dict) -> None:
        self._db.execute(
            """INSERT INTO breakdowns (judgment_id, prompt_version, model, content) VALUES (%s, %s, %s, %s)
               ON CONFLICT (judgment_id, prompt_version, model)
               DO UPDATE SET content = EXCLUDED.content, created_at = now()""",
            [judgment_id, prompt_version, model, json.dumps(content)],
        )


class LlmCallLog:
    """Metadata about language-model calls. Never stores questions or prompts."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def calls_today(self) -> int:
        row = self._db.fetch_one(
            "SELECT count(*) AS n FROM llm_calls WHERE ts >= date_trunc('day', now() AT TIME ZONE 'utc') "
            "AT TIME ZONE 'utc' AND outcome <> 'capped'"
        )
        return row["n"] if row else 0

    def record(self, **fields: object) -> None:
        columns = ", ".join(fields)
        placeholders = ", ".join(f"%({k})s" for k in fields)
        self._db.execute(f"INSERT INTO llm_calls ({columns}) VALUES ({placeholders})", fields)


class StatuteRepository:
    """Statute browser over judgment_acts (section references) and the paragraph text they came from."""

    def __init__(self, db: Database, judgments: JudgmentRepository) -> None:
        self._db = db
        self._judgments = judgments

    def _section_rows(self, section: str | None = None) -> list[dict]:
        if section is None:
            return self._db.fetch_all(
                "SELECT judgment_id, act_display, section FROM judgment_acts WHERE section IS NOT NULL"
            )
        return self._db.fetch_all(
            "SELECT judgment_id, act_display, section FROM judgment_acts WHERE section = %s", [section]
        )

    def index(self) -> StatuteIndex:
        from nyaya.text import statute_key

        names: dict[str, dict[str, int]] = {}
        judgments: dict[str, set[str]] = {}
        sections: dict[str, dict[str, set[str]]] = {}
        for row in self._section_rows():
            key = statute_key(row["act_display"])
            if key is None:
                continue
            names.setdefault(key, {}).setdefault(row["act_display"], 0)
            names[key][row["act_display"]] += 1
            judgments.setdefault(key, set()).add(row["judgment_id"])
            sections.setdefault(key, {}).setdefault(row["section"], set()).add(row["judgment_id"])
        acts = [
            StatuteSummary(
                key=key,
                name=max(names[key], key=names[key].get).split(",")[0].strip(),
                judgments=len(judgments[key]),
                sections=sorted(
                    (SectionCount(section=sec, judgments=len(ids)) for sec, ids in sections[key].items()),
                    key=lambda s: (-s.judgments, int(re.match(r"\d+", s.section).group())),
                ),
            )
            for key in judgments
        ]
        return StatuteIndex(acts=sorted(acts, key=lambda a: (-a.judgments, a.name)))

    def section(self, key: str, section: str):
        from nyaya.text import statute_key

        ids: set[str] = set()
        names: dict[str, int] = {}
        for row in self._section_rows(section):
            if statute_key(row["act_display"]) == key:
                ids.add(row["judgment_id"])
                names[row["act_display"]] = names.get(row["act_display"], 0) + 1
        if not ids:
            return None
        name = max(names, key=names.get).split(",")[0].strip()
        found = []
        for judgment_id, summary in self._judgments.summaries(ids).items():
            hits = []
            for paragraph in self._judgments.paragraphs(judgment_id):
                if any(m.key == key and m.section == section for m in find_statute_references(paragraph.text)):
                    hits.append(StatuteParagraph(label=paragraph.label, text=paragraph.text))
            if hits:
                found.append(StatuteJudgment(judgment=summary, paragraphs=hits))
        found.sort(key=lambda j: j.judgment.decision_date or date.min, reverse=True)
        return StatuteSectionPage(key=key, name=name, section=section, judgments=found)
