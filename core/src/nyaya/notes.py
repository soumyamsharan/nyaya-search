"""Shared research notes: create, read, renew and revoke read-only links to corpus paragraphs."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from nyaya.db import Database
from nyaya.errors import NoteWithdrawnError, NotFoundError

LIFETIME = timedelta(days=30)
MAX_ITEMS = 200


@dataclass(frozen=True)
class NoteItem:
    judgment_id: str
    label: str


@dataclass(frozen=True)
class CreatedNote:
    id: str
    owner_token: str  # shown once; only its hash is stored
    expires_at: datetime


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class NoteRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, items: list[NoteItem]) -> CreatedNote:
        note_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + LIFETIME
        self._db.execute(
            "INSERT INTO shared_notes (id, items, owner_token_hash, expires_at) VALUES (%s, %s, %s, %s)",
            [note_id, _json([{"judgment_id": i.judgment_id, "label": i.label} for i in items]), _hash(token), expires],
        )
        return CreatedNote(note_id, token, expires)

    def _row(self, note_id: str) -> dict:
        try:
            uuid.UUID(note_id)
        except ValueError as exc:
            raise NotFoundError("note not found") from exc
        row = self._db.fetch_one(
            "SELECT items, owner_token_hash, expires_at, revoked_at FROM shared_notes WHERE id = %s", [note_id]
        )
        if row is None:
            raise NotFoundError("note not found")
        return row

    def read(self, note_id: str) -> tuple[list[dict], datetime]:
        """The note's references and its expiry. Raises NoteWithdrawnError if revoked or expired."""
        row = self._row(note_id)
        if row["revoked_at"] is not None:
            raise NoteWithdrawnError("This note has been withdrawn.")
        if row["expires_at"] <= datetime.now(UTC):
            raise NoteWithdrawnError("This note has expired. Ask the sender for a new link.")
        return row["items"], row["expires_at"]

    def _owned(self, note_id: str, owner_token: str) -> None:
        row = self._row(note_id)
        if row["owner_token_hash"] != _hash(owner_token):
            raise NotFoundError("note not found")  # same answer as an unknown id: no hint that it exists

    def renew(self, note_id: str, owner_token: str) -> datetime:
        self._owned(note_id, owner_token)
        expires = datetime.now(UTC) + LIFETIME
        self._db.execute(
            "UPDATE shared_notes SET expires_at = %s WHERE id = %s AND revoked_at IS NULL", [expires, note_id]
        )
        return expires

    def revoke(self, note_id: str, owner_token: str) -> None:
        self._owned(note_id, owner_token)
        self._db.execute(
            "UPDATE shared_notes SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL", [note_id]
        )


def _json(value: object) -> str:
    import json

    return json.dumps(value)


def resolve(items: list[dict], judgments) -> list[dict]:
    """Read each stored reference from the corpus. A reference whose paragraph no longer exists is marked missing."""
    summaries = judgments.summaries(i["judgment_id"] for i in items)
    paragraphs = {}
    out = []
    for item in items:
        judgment_id, label = item["judgment_id"], item["label"]
        summary = summaries.get(judgment_id)
        if judgment_id not in paragraphs:
            paragraphs[judgment_id] = {p.label: p for p in judgments.paragraphs(judgment_id)} if summary else {}
        paragraph = paragraphs[judgment_id].get(label)
        out.append({
            "judgment": summary,
            "label": label,
            "text": paragraph.text if paragraph else None,
        })
    return out
