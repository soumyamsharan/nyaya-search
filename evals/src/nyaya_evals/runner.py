"""Retrieval evaluation: recall@10, MRR and p95 latency for each search setup, against local services or a
deployed API. Exits non-zero when hybrid + reranker does worse than keyword search."""

import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Protocol

import httpx
import typer
import yaml

from nyaya.domain import SearchFilters, SearchMode
from nyaya.text import parse_query

app = typer.Typer(add_completion=False)
DEFAULT_QUERIES = Path(__file__).resolve().parents[2] / "queries.yaml"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
K = 10


@dataclass(frozen=True)
class EvalQuery:
    id: str
    query: str
    expected: list[str]
    author: str


@dataclass
class ModeResult:
    mode: str
    recall_at_10: float
    mrr: float
    p95_ms: int
    queries: int


class SearchBackend(Protocol):
    def ranked_ids(self, query: str, mode: SearchMode) -> list[str]: ...
    def exists(self, judgment_id: str) -> bool: ...
    def describe(self) -> dict: ...


class LocalBackend:
    def __init__(self) -> None:
        from nyaya.config import get_settings
        from nyaya.container import build_services

        self._settings = get_settings()
        self._services = build_services(self._settings)

    def ranked_ids(self, query: str, mode: SearchMode) -> list[str]:
        hits = self._services.search.rank(parse_query(query), SearchFilters(), mode)
        return [h.judgment_id for h in hits]

    def exists(self, judgment_id: str) -> bool:
        return self._services.judgments.exists(judgment_id)

    def describe(self) -> dict:
        s = self._settings
        return {"target": "local", "reranker_backend": s.reranker_backend, "rerank_depth": s.rerank_depth,
                "rerank_max_tokens": s.rerank_max_tokens, "embedding_model": s.embedding_model,
                "reranker_model": s.reranker_model}


class HttpBackend:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=30)

    def ranked_ids(self, query: str, mode: SearchMode) -> list[str]:
        response = self._http.get("/v1/search", params={"q": query, "mode": mode.value})
        response.raise_for_status()
        return [r["judgment"]["id"] for r in response.json()["results"]]

    def exists(self, judgment_id: str) -> bool:
        return self._http.get(f"/v1/judgments/{judgment_id}").status_code == 200

    def describe(self) -> dict:
        return {"target": self._base_url}


def load_queries(path: Path) -> list[EvalQuery]:
    return [EvalQuery(**item) for item in yaml.safe_load(path.read_text())["queries"]]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(pct / 100 * len(ordered)) - 1)]


def score(ranked: list[str], expected: list[str]) -> tuple[float, float]:
    """(recall@10, reciprocal rank) for one query."""
    top = ranked[:K]
    recall = len(set(top) & set(expected)) / len(expected)
    rr = next((1 / rank for rank, jid in enumerate(top, start=1) if jid in expected), 0.0)
    return recall, rr


def evaluate(backend: SearchBackend, queries: list[EvalQuery], mode: SearchMode) -> ModeResult:
    recalls, rrs, latencies = [], [], []
    for q in queries:
        started = time.monotonic()
        ranked = backend.ranked_ids(q.query, mode)
        latencies.append((time.monotonic() - started) * 1000)
        recall, rr = score(ranked, q.expected)
        recalls.append(recall)
        rrs.append(rr)
    n = len(queries)
    return ModeResult(mode.value, round(sum(recalls) / n, 3), round(sum(rrs) / n, 3),
                      int(percentile(latencies, 95)), n)


def gate_failure(results: dict[str, ModeResult]) -> str | None:
    bm25, best = results.get(SearchMode.BM25.value), results.get(SearchMode.HYBRID_RERANK.value)
    if bm25 and best and best.recall_at_10 < bm25.recall_at_10:
        return f"hybrid_rerank recall@10 {best.recall_at_10} < bm25 {bm25.recall_at_10}"
    return None


@app.command()
def main(
    queries: Annotated[Path, typer.Option(help="Eval set YAML")] = DEFAULT_QUERIES,
    api_url: Annotated[str | None, typer.Option(help="Evaluate a deployed API instead of local services")] = None,
    mode: Annotated[list[SearchMode] | None, typer.Option(help="Repeatable; default all four")] = None,
) -> None:
    backend: SearchBackend = HttpBackend(api_url) if api_url else LocalBackend()
    entries = load_queries(queries)
    valid = [q for q in entries if q.expected and all(backend.exists(j) for j in q.expected)]
    for q in entries:
        if q not in valid:
            typer.echo(f"INVALID entry {q.id}: expected judgment(s) not in corpus; excluded")
    if not valid:
        raise typer.Exit(code=1)

    results = {m.value: evaluate(backend, valid, m) for m in (mode or list(SearchMode))}
    typer.echo(f"\n{'setup':<15}{'recall@10':>10}{'MRR':>8}{'p95 ms':>9}")
    for r in results.values():
        typer.echo(f"{r.mode:<15}{r.recall_at_10:>10.3f}{r.mrr:>8.3f}{r.p95_ms:>9}")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{stamp}.json"
    failure = gate_failure(results)
    out.write_text(json.dumps({
        "timestamp": stamp,
        "config": backend.describe(),
        "queries": len(valid),
        "invalid": [q.id for q in entries if q not in valid],
        "results": [asdict(r) for r in results.values()],
        "gate": failure or "passed",
    }, indent=2))
    typer.echo(f"\nsaved {out}")
    if failure:
        typer.echo(f"GATE FAILED: {failure}")
        raise typer.Exit(code=1)
