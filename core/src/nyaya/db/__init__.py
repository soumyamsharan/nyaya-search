"""Thin database access helpers. All SQL is parameterised; nothing here builds SQL from user input."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    def __init__(self, url: str, min_size: int = 1, max_size: int = 8) -> None:
        self._pool = ConnectionPool(
            url, min_size=min_size, max_size=max_size, kwargs={"row_factory": dict_row}, open=True
        )

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        with self._pool.connection() as conn:
            yield conn

    def fetch_all(self, sql: str, params: Sequence[Any] | dict[str, Any] | None = None) -> list[dict]:
        with self.connection() as conn:
            return conn.execute(sql, params).fetchall()

    def fetch_one(self, sql: str, params: Sequence[Any] | dict[str, Any] | None = None) -> dict | None:
        with self.connection() as conn:
            return conn.execute(sql, params).fetchone()

    def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] | None = None) -> None:
        with self.connection() as conn:
            conn.execute(sql, params)

    def close(self) -> None:
        self._pool.close()

    def migrate(self) -> list[str]:
        """Apply pending migrations in filename order; returns the names applied."""
        applied: list[str] = []
        with self.connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY)")
            done = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations").fetchall()}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.name in done:
                    continue
                with conn.transaction():
                    conn.execute(path.read_text())
                    conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", [path.name])
                applied.append(path.name)
        return applied
