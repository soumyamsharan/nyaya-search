# Nyaya Search

Find Supreme Court of India precedents by describing your case's facts in plain words. Every result, summary line
and answer is pinned to the paragraph it came from, and each judgment shows which later judgments cite it.

**Live:** _link goes here after deployment_ · **Corpus:** Supreme Court judgments 2024 onwards (Digital SCR format)

## What it does

- **Fact-pattern search:** keyword (BM25) and semantic (BGE-M3) retrieval fused with reciprocal rank fusion, then a
  cross-encoder reranker. Also supports quoted phrases, citation lookup (`(2019) 5 SCC 123`, `2024 INSC 735`) and
  filters for year, judge and Act/section.
- **Reading:** numbered paragraphs, the law reporter's headnotes (labelled as the reporter's), a facts/issues/held/
  ratio breakdown, follow-up questions answered only from the judgment, pinpoint citation copy, and a Markdown
  research note.
- **Citation graph:** cites and cited-by with the citing paragraph. Overruling language in a citing paragraph is shown
  as evidence, never as a verdict.
- **Grounding:** case names and citations come only from stored data. Every generated sentence must cite a supplied
  paragraph that supports it, or it is dropped.

## Architecture

```
Browser ──► Next.js (Vercel) ──► FastAPI /v1 (Caddy, HTTPS) ──► Postgres + pg_search (BM25) + pgvector
                                     │  BGE-M3 embedder + bge-reranker-v2-m3 (CPU in production)
                                     └─► LLM via any OpenAI-compatible API (Groq in production, Ollama locally)
Ingestion (on a laptop GPU): S3 open dataset → PDF → paragraphs/front matter → embeddings → citation graph
```

| Path | What |
|---|---|
| `core/` | Domain, parsing, search, grounding, LLM client, repositories (`nyaya` package) |
| `pipeline/` | Ingestion CLI: `pipeline migrate / sync / extract / index / citations / all` |
| `api/` | REST API (`/v1/search`, `/v1/judgments/{id}`, `…/breakdown`, `…/questions`, `…/citations`, `/healthz`) |
| `web/` | Next.js app |
| `evals/` | Retrieval eval set and runner |
| `deploy/`, `scripts/` | Production Compose, Caddyfile, server hardening, DB shipping, backups, restore drill |

## Run locally

Needs Docker, [uv](https://docs.astral.sh/uv/), Node 20+, the AWS CLI and Ollama.

```bash
cp .env.example .env                      # set POSTGRES_PASSWORD (the app adds it to DATABASE_URL)
docker compose up -d db
uv sync
uv run pipeline all                       # migrate, download 2024–2026, extract, embed, build citations
ollama pull qwen2.5:7b                    # or point LLM_* at Groq
uv run api                                # http://localhost:8000/docs
cd web && npm install && npm run dev      # http://localhost:3000
```

Behind a TLS-inspecting proxy, model downloads may stall. Download the model folders some other way, then set
`EMBEDDING_MODEL` and `RERANKER_MODEL` to the local paths.

## Tests and evals

```bash
uv run pytest                     # unit tests (no services needed)
uv run pytest -m integration      # against the local database, models and LLM
uv run evals                      # recall@10, MRR, p95 for bm25 / vector / hybrid / hybrid_rerank
```

| Search setup | Recall@10 | MRR | p95 latency |
|---|---|---|---|
| _filled from `evals/results/` after a run_ | | | |

## Deploy

1. **Server:** an Oracle Cloud Always Free Ampere A1 instance, or a Hetzner CAX21 as fallback. Run
   `scripts/server-setup.sh` to set up a firewall allowing 22/80/443, key-only SSH, automatic updates and Docker.
2. **Point the API hostname** (e.g. a DuckDNS name) at the server's IP.
3. **Build and push the image:**
   `docker buildx build --platform linux/arm64 -f api/Dockerfile -t ghcr.io/<you>/nyaya-api:<tag> --push .`
4. **Copy files to the server:** `deploy/compose.prod.yml`, `deploy/Caddyfile`, `scripts/`, and a filled-in
   `deploy/.env.example` saved as `.env` (chmod 600).
5. **Start the stack:** `docker compose -f compose.prod.yml up -d`.
6. **Ship the data:** `scripts/ship-db.sh ubuntu@<server>`. It restores into a new database and switches to it,
   keeping the old one for rollback.
7. **Deploy the web app:** a Vercel project on `web/` with `NEXT_PUBLIC_API_URL=https://<api-host>`.
8. **Monitoring and backups:** an UptimeRobot check on `https://<api-host>/healthz`, and a cron entry for
   `scripts/backup.sh`. Run `scripts/restore-drill.sh` once.

## Limitations

- Only 2024 onwards. Older years use an OCR'd layout that is not parsed yet, so many citations to older cases show
  as plain text.
- "Overruling language found" means a later paragraph uses words like *overruled* near a citation. Read that
  paragraph; it is not a verdict.
- Generated text is a research aid. Read the judgment before citing it.

## Data and licence

Judgments come from the [Indian Supreme Court Judgments](https://registry.opendata.aws/indian-supreme-court-judgments/)
open dataset (CC-BY-4.0). Credit to its maintainers.
