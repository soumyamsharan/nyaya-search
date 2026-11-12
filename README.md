# Nyaya Search

Find Supreme Court of India judgments by describing the facts of your case in plain words. Every result, summary
line and answer is pinned to the paragraph it came from, and each judgment shows the earlier cases it cites and the
later judgments that cite it.

- **Live site:** https://nyaya-search-six.vercel.app
- **Backend API:** https://soumyamsharan-nyaya-search-api.hf.space (`/docs` for the interactive reference, `/healthz` for status)
- **Corpus:** 1,920 Supreme Court judgments decided 2024–2026 (Digital SCR format), 71,426 numbered paragraphs
- **Status:** feature-complete for v1; the eval numbers are not yet measured (see *Evaluation*)

## What it does

**Search**
- Describe the facts in plain words. Keyword (BM25) and meaning-based (BGE-M3) retrieval are merged, then a
  cross-encoder re-ranks the results. Each result shows the paragraph that matched, with a link to it.
- Quoted phrases and the operators `AND`, `OR` and `NOT` (capitals), e.g. `eviction NOT "bona fide requirement"`.
- Citation lookup, e.g. `2024 INSC 874`, `[2024] 10 S.C.R. 108` or `(2019) 5 SCC 123`, including citations resolved
  through the reporters' parallel-citation lists.
- Filters: decision date range, judges on the bench (several, all required), author judge, outcome, Act and section,
  and **Match in** a paragraph role (e.g. only the court's reasoning and conclusion).
- Typo tolerance: a "Did you mean…?" suggestion built from the corpus's own vocabulary, one-letter typo tolerance for
  keywords when a query contains unknown words, and tolerant judge and author names with autocomplete.
- "No relevant judgments found" instead of weak matches.

**Reading a judgment**
- Full text in numbered paragraphs with the printed numbers, labelled numbering where the judgment has none, and
  opinions labelled separately (e.g. O2-3).
- The law reporter's headnotes, labelled as the reporter's and not the court's, with `[Para N]` links.
- Paragraph roles (Facts, Issue, Petitioner's and Respondent's argument, Statute, Precedent, Court's reasoning,
  Conclusion), shown as tags and usable as filter chips, marked as machine-assigned.
- **Cites cases only:** shows just the paragraphs that refer to an earlier case (a citation, a case name, "(supra)" or
  a "[See: …]" reference).
- **Inline citations:** each citation in the text is highlighted; it links to that judgment when it is in the corpus,
  and is marked "not in the corpus" otherwise.
- **Copy with citation:** the paragraph text in quotation marks followed by the case name, citation and ¶ number.
- **Research note:** collect paragraphs from any judgments, export them as Markdown. Kept only in your browser.
- Original PDF link, and "Back to where you were" after following a ¶ link.

**AI features** (every generated sentence must cite a paragraph that supports it, or it is dropped)
- **Breakdown:** facts, issues, held and ratio, with paragraph links. Generated once per judgment and cached.
- **Ask about this judgment:** answers from that judgment's text only, or says it doesn't address the question.

**Citation graph**
- Cites and cited-by, with the citing paragraph. Overruling language in a citing paragraph is shown as evidence,
  never as a verdict.

**Trust and privacy**
- Case names and citations come only from stored data, never from the AI.
- Search text is processed on our backend and never sent to a third party. Only the question and the paragraphs it
  needs go to the AI provider, and the page says so.
- Queries and questions are not logged or stored; logs keep method, route, status and timing only.
- Per-IP rate limits, and a daily cap on AI calls (300 a day). Search keeps working when the cap is reached.

## Architecture

```
Browser ──► Vercel (Next.js website) ──► Hugging Face Space (Docker, HTTPS)
                                          ├─ FastAPI /v1 (CPU)
                                          ├─ Postgres 17 + pg_search (BM25) + pgvector (BGE-M3 vectors)
                                          ├─ BGE-M3 embedder, bge-reranker-v2-m3 (CPU)
                                          └─► Groq (gpt-oss-20b) for breakdowns and answers

Ingestion (on the developer's Mac, GPU): open S3 dataset → PDFs → paragraphs, front matter, case names,
  citations, roles, vocabulary → embeddings → database dump published for the Space
```

| Path | What |
|---|---|
| `core/` | Domain models, PDF and judgment parsing, search, spelling, roles, citations, grounding, LLM client (`nyaya` package) |
| `pipeline/` | Ingestion CLI: `pipeline migrate`, `sync`, `extract`, `roles`, `vocabulary`, `index`, `citations`, `all` |
| `api/` | REST API (`/v1`) and `/healthz` |
| `web/` | Next.js (App Router, TypeScript, Tailwind) website |
| `evals/` | Retrieval eval set (`queries.yaml`) and runner |
| `deploy/hf-space/` | Single-container build for the Hugging Face Space (ParadeDB + API, models and data baked in) |
| `deploy/` | Production Compose and Caddyfile for a VPS (alternative to the Space) |
| `scripts/` | `publish_hf.py` (publish the database and Space), server hardening, DB shipping, backups, restore drill |
| `openspec/` | Specifications and change history (see *Specifications*) |

### REST API (`/v1`)

| Endpoint | Purpose |
|---|---|
| `GET /v1/search` | Search with `q`, `judge` (repeatable), `author`, `outcome`, `role` (repeatable), `date_from`, `date_to`, `year_from`, `year_to`, `act`, `section`. Returns results, a `suggestion` and a message. |
| `GET /v1/judges` | Judges on any bench, with judgment counts |
| `GET /v1/judgments/{id}` | Metadata, reporter front matter, and paragraphs with roles, `cites_cases` flag and citation references |
| `GET /v1/judgments/{id}/breakdown` | Facts, issues, held and ratio (AI, cached) |
| `POST /v1/judgments/{id}/questions` | Ask a question about one judgment (AI) |
| `GET /v1/judgments/{id}/citations` | Cites, cited-by, unresolved citations and overruling evidence |
| `GET /healthz` | Health check (not rate limited) |

Errors use one format: `{"error": {"code": "...", "message": "..."}}`, with 404, 422, 429 and 503 status codes.

## Models

| Use | Model | Where it runs |
|---|---|---|
| Paragraph and query embeddings | BGE-M3 (BAAI) | Backend CPU (Space); Mac GPU for ingestion |
| Re-ranking and fact-checking AI sentences | bge-reranker-v2-m3 (BAAI) | Backend CPU; re-ranks the top 5 candidates at 128 tokens |
| Breakdown and Q&A text | gpt-oss-20b (OpenAI open weights, served by Groq) | Groq. Locally, Qwen 2.5 7B through Ollama. |

Paragraph roles, citation extraction, spelling suggestions, judge matching and the citation graph are rules and
database queries, not AI.

## Run locally

Needs Docker, [uv](https://docs.astral.sh/uv/), Node 22+, the AWS CLI, and Ollama (for local AI answers).

```bash
cp .env.example .env                      # set POSTGRES_PASSWORD; the app adds it to DATABASE_URL
docker compose up -d db
uv sync
uv run pipeline all                       # migrate, download 2024–2026, extract, roles, vocabulary, embed, citations
ollama pull qwen2.5:7b                    # or set LLM_* to Groq
uv run api                                # http://localhost:8000/docs
cd web && npm install && npm run dev      # http://localhost:3000
```

Behind a TLS-inspecting proxy, model downloads can stall. Download the model folders another way and point
`EMBEDDING_MODEL` and `RERANKER_MODEL` at them.

## Tests

```bash
uv run pytest                     # 122 unit tests, no services needed
uv run pytest -m integration      # 42+ tests against the local database, models and LLM (several minutes)
cd web && npx tsc --noEmit && npx eslint src
```

Integration tests cover search, filters, operators, citations, roles, typo tolerance, the breakdown and Q&A, the
daily cap, and re-ingestion determinism. The latency check (p95 search under 3 s) is part of `-m integration`.

## Evaluation

`evals/queries.yaml` holds 21 fact-pattern queries, drafted from the reporters' issue statements. An advocate should
review them before the numbers are quoted.

```bash
uv run evals                      # recall@10, MRR and p95 for bm25, vector, hybrid, hybrid_rerank
uv run evals --api-url https://soumyamsharan-nyaya-search-api.hf.space   # against the live backend
```

| Search setup | Recall@10 | MRR | p95 latency |
|---|---|---|---|
| Keyword (BM25) | _not yet measured_ | | |
| Semantic (BGE-M3) | _not yet measured_ | | |
| Hybrid | _not yet measured_ | | |
| Hybrid + reranker | _not yet measured_ | | |

The runner exits with an error if hybrid + reranker scores below keyword search. Results are saved to `evals/results/`.

Quality checks done so far: paragraph role labels were spot-checked on 40 random paragraphs per round (about 72%
correct; facts, reasoning and conclusions are most reliable); the int8 reranker keeps scores correlated at 0.986
with full precision.

## Deploy

**Current setup (free):**
1. **Backend:** a Hugging Face Docker Space, built from `deploy/hf-space/`. `scripts/publish_hf.py db` uploads the
   database dump as a dataset; `scripts/publish_hf.py space --origin https://<site>` uploads the Space build.
   Set the Space secret `LLM_API_KEY` (Groq key) and the variables `LLM_MODEL`, `LLM_DAILY_CAP`, `ALLOWED_ORIGINS`.
   Free Spaces can sleep after about 48 idle hours; the website tells visitors it is waking up.
2. **Website:** a Vercel project with root directory `web` and `NEXT_PUBLIC_API_URL` set to the Space's URL.
   Pushing to `main` redeploys it.

**Republishing data:** after re-ingesting, run `uv run pipeline all` locally, then `publish_hf.py db` and
`publish_hf.py space` again.

**Alternative (always on, paid or Oracle Always Free):** `deploy/compose.prod.yml` with Caddy for HTTPS, `scripts/server-setup.sh`
for firewall and SSH hardening, `scripts/ship-db.sh` to restore the database, `scripts/backup.sh` for nightly backups,
and `scripts/restore-drill.sh` to test restores.

## Specifications

Each feature is an OpenSpec change under `openspec/changes/`, with a proposal, design, spec deltas and tasks:

| Change | Covers |
|---|---|
| `build-nyaya-search-mvp` | Ingestion, search, reading, citation graph, grounding, evaluation, public access |
| `add-paragraph-roles-and-search-operators` | Paragraph roles, AND/OR/NOT, date, author, judge and outcome filters |
| `add-typo-tolerance` | "Did you mean", fuzzy keywords, judge list and tolerant name matching |
| `add-citation-annotations` | Cites-cases filter, inline citation links, broader citation formats, quoted-numbering fix |

## Limitations

- **Coverage:** only Supreme Court judgments from 2024 onwards. Older judgments use an OCR'd layout that isn't parsed
  yet, so citations to older cases appear as plain text. No High Courts, tribunals, daily orders or statutes.
- **Paragraph roles** are rule-based, about 72% accurate on spot checks. Treat them as hints.
- **Numbering:** about 13 judgments have no printed paragraph numbers and use derived numbers, flagged in the view.
- **AI** answers and breakdowns are research aids. Read the judgment before citing it. The "overruling language" flag
  means a later paragraph uses words like *overruled* near a citation; it is not a verdict.
- **Speed and limits** on the free backend: search takes about 2–6 s, AI answers about 10–15 s, and the Space sleeps
  after idle periods.
- **Not built:** Hindi, user accounts and saved folders, alerts, PDF printing with notes, and drafting or outcome
  prediction (deliberately out of scope).

## Data and licence

Judgments come from the [Indian Supreme Court Judgments](https://registry.opendata.aws/indian-supreme-court-judgments/)
open dataset (CC-BY-4.0). Credit to its maintainers. Generated summaries and answers are not legal advice.
