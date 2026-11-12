"""Ingestion run reports: counts saved to ingest_runs and a pass/fail outcome."""

import json
from collections import Counter
from dataclasses import dataclass, field

from nyaya.db import Database


@dataclass
class RunReport:
    stage: str
    counts: Counter = field(default_factory=Counter)
    failures: list[tuple[str, str]] = field(default_factory=list)

    def fail(self, item: str, reason: str) -> None:
        self.counts["failed"] += 1
        self.failures.append((item, reason))

    def failure_share(self) -> float:
        processed = self.counts["processed"]
        return self.counts["failed"] / processed if processed else 0.0

    def outcome(self, max_failure_share: float) -> str:
        return "failed" if self.failure_share() > max_failure_share else "ok"

    def save(self, db: Database, max_failure_share: float) -> str:
        outcome = self.outcome(max_failure_share)
        payload = dict(self.counts) | {"failures": [f"{i}: {r}" for i, r in self.failures[:50]]}
        db.execute(
            "INSERT INTO ingest_runs (stage, finished_at, counts, outcome) VALUES (%s, now(), %s, %s)",
            [self.stage, json.dumps(payload), outcome],
        )
        return outcome

    def summary(self) -> str:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(self.counts.items()))
        return f"[{self.stage}] {parts} (failure share {self.failure_share():.1%})"
