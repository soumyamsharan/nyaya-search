## Context

Greenfield repo. See proposal.md for motivation and specs/ for required behaviour. Constraints that shape the approach:

- **Time:** 1–2 days of build, one developer. Every decision below prefers the simpler option that still meets the specs.
- **Machine:** Apple Silicon Mac, 16 GB RAM, Docker Desktop VM of about 8 GB, ~70 GB free disk. Docker on macOS has no GPU access; native processes can use Metal (MPS).
- **Production:** an Oracle Cloud Always Free Ampere A1 (Arm64) server, CPU only, with about 2 OCPU and 12 GB RAM (limits must be confirmed at sign-up). The web app is on Vercel's free plan. The site must stay up for recruiters, so it cannot sleep and cannot depend on the Mac.
- **Data, as checked on 2026-11-11** (`s3://indian-supreme-court-judgments`, public, `--no-sign-request`):
  - `data/pdf/year=YYYY/english/<path>_EN.pdf`, one judgment per PDF, named after its SCR volume and page range. About 780–900 PDFs a year, 175–400 MB a year.
  - `metadata/parquet/year=YYYY/metadata.parquet` with `title, petitioner, respondent, judge, citation` (SCR, e.g. `[2024] 10 S.C.R. 108`), `case_id` (neutral, e.g. `2024 INSC 735`), `cnr, decision_date` (DD-MM-YYYY), `disposal_nature, path`. `judge` holds only one name; the full bench is printed in the PDF.
  - **2024 PDFs are in the Digital SCR layout:** a bench line `[A and B,* JJ.]` (`*` = author), then reporter front matter with labelled sections (`Issue for Consideration`, `Headnotes` with `[Para N]` refs, `Case Law Cited` with parallel citations `[2007] 3 SCR 507 : (2007) 3 SCC 755`, `List of Acts`, `List of Keywords`, `Case Arising From`, `Appearances for Parties`), then `Judgment / Order of the Supreme Court`, the author line `X, J.` and paragraphs `1.` … `N.`. Running headers repeat the SCR citation and case title on each page, and footnotes use superscript markers.
  - **2017 and 2021 PDFs use an older OCR'd layout:** margin letters A–H, OCR noise, no section labels. That layout is out of scope here.

## Goals / Non-Goals

**Goals:**
- One Postgres database holds everything: metadata, paragraphs, vectors, BM25 index, citations and caches.
- The paragraph `(judgment_id, seq)` is the unit for search, display, citation and grounding.
- Models sit behind small interfaces, so the LLM provider, embedding model or reranker can change through config.

**Non-Goals:**
- Parsing the pre-2023 OCR layout, OCR itself, and Hindi.
- Splitting paragraphs into sub-chunks (see Decision 4).
- Kubernetes, Grafana, and multi-server or high-availability setups. Terraform and CI deploys are stretch goals only.
- Running ingestion or embedding on the server: the server only serves queries.
- Accounts and server-side storage of user data.

## Decisions

### 1. Repo layout and toolchain
```
nyaya-search/
  core/        Python package: db access, parsing, search, rerank, grounding, citations, llm client
  pipeline/    Typer CLI: sync, extract, index, citations, report  (imports core)
  api/         FastAPI app (imports core)
  evals/       queries.yaml + runner (imports core)
  web/         Next.js (App Router, TypeScript, Tailwind)
  docker-compose.yml   Postgres only
  .env.example
```
- **Python packages:** a uv workspace on Python 3.12 (3.14 lacks wheels for parts of the ML stack), with dependencies locked in `uv.lock`.
- **Why one `core` package:** the pipeline, API and evals all need the same search and parsing code. Separate services would only add overhead in a 2-day build.

### 2. Database: ParadeDB image (Postgres + pg_search + pgvector)
- **Choice:** one Docker image with BM25 (`pg_search`) and vectors (`pgvector`) built in, pinned to an exact version tag.
- **Network and memory:** the port is bound to `127.0.0.1` only, the password comes from `.env`, and Docker's memory limit is set to about 4 GB.
- **Alternatives:**
  - Stock Postgres full-text search: `ts_rank` is not BM25 and does worse on long legal text. It stays as the fallback if the ParadeDB image fails on arm64.
  - OpenSearch: one more service, and it needs more RAM.
- **Vectors:** `halfvec(1024)` with an HNSW index (cosine). Filtered vector queries use pgvector's iterative index scan, so filters don't starve the top-k.

### 3. Data model (core tables)
| Table | Key fields |
|---|---|
| `judgments` | `id` (dataset `path`), `title`, `petitioner`, `respondent`, `decision_date`, `bench text[]`, `author`, `neutral_citation`, `scr_citation`, `pdf_url`, `status` (ok / scanned / failed + reason), `extractor_version` |
| `paragraphs` | `id`, `judgment_id`, `seq` (1..n within judgment), `opinion_idx`, `label` (`"14"`, or `"O2-3"` for opinion 2 ¶3), `label_derived bool`, `text`, `embedding halfvec(1024)`; BM25 index on `text` |
| `front_matter` | `judgment_id`, `section` (issue / headnotes / case_law_cited / acts / keywords / …), `text` |
| `judgment_acts` | `judgment_id`, `act_norm`, `section` (nullable) |
| `citation_aliases` | `citation_norm` → `judgment_id`, or → `alias_group` before resolution |
| `citations` | `citing_judgment_id`, `citing_seq`, `raw`, `citation_norm`, `cited_judgment_id` (nullable), `overruling_language bool` |
| `breakdowns` | `judgment_id`, `prompt_version`, `model`, `content jsonb`, `created_at` |
| `llm_calls` | `ts`, `purpose`, `model`, `prompt_version`, `tokens_in/out`, `latency_ms`, `sentences_dropped`. **Never the question text** |
| `ingest_runs` | counts, thresholds, outcome |

- **Upserts:** ingestion upserts by `(judgment_id, extractor_version)`. A judgment is re-parsed only when the PDF or the extractor version changes, which keeps paragraph ids deterministic.

### 4. One paragraph = one search unit (no sub-chunking)
- **Why it works:** BGE-M3 accepts long inputs, and Supreme Court paragraphs are usually short (median ≈145 tokens, 90th percentile ≈500). Embedding whole paragraphs keeps the "matched ¶14" mapping exact.
- **Truncation (`EMBED_MAX_TOKENS`, default 512):** measured on the dev Mac, 512 tokens embeds about 40% faster than 1,024 (19 vs 14 paragraphs/s). About 10% of paragraphs are longer; only their vector is truncated, and BM25 still indexes their full text. The first ~13k paragraphs were embedded at 1,024 before this was lowered. That is the same model, so the vectors are compatible.
- **Reranker input:** truncated at 512 tokens.
- **Alternative rejected:** 300–500 token chunks with paragraph back-references. They add a mapping layer and help no spec.

### 5. Parsing the Digital SCR layout
- **Span-level extraction:** PyMuPDF gives text spans with their font sizes. Running headers (the SCR citation and case title repeated on every page) and footnote blocks (small font at the bottom of the page) are dropped. Superscript footnote markers are dropped from the text.
- **Front matter:** front matter is everything before `Judgment / Order of the Supreme Court`. It is split on the known section labels, and the bench and author come from the `[… JJ.]` line.
- **Paragraph detection:** a line starting `N.` opens a paragraph only when N = previous + 1. A reset to `1.` after an author line (`X, J.`) starts a new opinion (`opinion_idx + 1`). Anything else, such as numbered lists inside quotations, stays inside the current paragraph.
- **Fallback:** if no numbering is found, split on blank-line blocks, set `label_derived = true` and number them 1..n.
- **Scanned PDFs:** fewer than about 200 extractable characters per page on average marks the judgment `scanned`.
- **`extractor_version`:** a constant bumped on any parser change.

### 6. Hybrid retrieval and reranking
```
query ──► is it a citation?  ──yes──► citation_aliases lookup ──► single result / "not in corpus"
   │no
   ├─► BM25 over paragraphs (top 100, filters, quoted phrases)          ┐
   └─► BGE-M3 query vector → HNSW (top 100, same filters)               ┘─► RRF (k=60)
          ─► best paragraph per judgment ─► top 50 ─► bge-reranker-v2-m3 ─► top 10
          ─► drop below relevance threshold ─► results (or "no relevant judgments")
```
- **Phrases:** quoted phrases go to pg_search as phrase queries. Vector-side candidates are post-filtered to paragraphs containing the phrase.
- **Relevance threshold:** a reranker score set from the eval set.
- **Where models run:**
  - Development: MPS in the native API process on the Mac.
  - Production: CPU in the API container on the Oracle server.
  - Models load once at startup in both cases.
- **CPU budget in production:**
  - The query embedder stays BGE-M3 at full precision, so query vectors match the stored ones. A short query is cheap.
  - The reranker reranks the **top 20** candidates (not 50), with each paragraph cut to **256 tokens**, using an int8-quantised ONNX export of bge-reranker-v2-m3.
  - The rerank depth, truncation and model are config values. The eval runner reports recall and latency for each setting, so the production choice is backed by numbers.
  - If the reranker still can't fit 3 s p95 on the server, production ships hybrid without rerank, and the eval table says so.
- **Interfaces:** `Embedder`, `Reranker` and `Retriever` are small interfaces, so the eval runner can switch between keyword-only, vector-only, hybrid and hybrid+rerank.

### 7. LLM client: OpenAI-compatible, Groq by default, Ollama as fallback
- **One client:** Groq and Ollama both expose OpenAI-compatible endpoints, so a single client with `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` from `.env` covers both. The model is a Groq-hosted open-weights instruct model, set in config.
- **Robustness:** timeouts and one retry, and a 429 from the provider maps to the "temporarily unavailable" state.
- **Output format:** the LLM returns JSON `{"sentences":[{"text":…, "paras":[seq,…]}]}` (Breakdown: grouped under facts / issues / held / ratio). Paragraphs are presented to the model as `[P<seq>] <text>`.
- **Context budget:** about 8k tokens per call, so a call fits inside free-tier tokens-per-minute limits:
  - **Breakdown:** the paragraphs referenced by reporter headnotes `[Para N]`, plus the first 5 and last 5 paragraphs, filled by document order up to the budget. Cached in `breakdowns` per `prompt_version` and model.
  - **Q&A:** hybrid + rerank restricted to the one judgment, top 8 paragraphs.

### 8. Grounding pipeline (no second LLM call)
1. Parse the JSON. Drop sentences with no `paras` or with `paras` outside the supplied set.
2. Drop sentences that contain a citation pattern or a `X v. Y` case name that doesn't appear in the supplied paragraphs.
3. Support check: the reranker scores (sentence, each cited paragraph). Keep the sentence if its best score is ≥ `SUPPORT_THRESHOLD`.
4. If nothing survives, return "no supported answer". Record `sentences_dropped`.

- **Why the reranker:** it is already loaded and costs no Groq quota, whereas an LLM judge would double the calls under a roughly 30 requests/minute limit.
- **Trade-off:** a relevance model is not an entailment model (see Risks).

### 9. Citation extraction and resolution
- **Patterns:** regexes for `(YYYY) [Supp] V SCC P`, `[YYYY] [Supp.] V S.C.R. P` / `SCR`, `AIR YYYY SC P` and `YYYY INSC N`. Each match is normalised by uppercasing and stripping spaces and punctuation, giving `citation_norm`.
- **Alias table:**
  - Each judgment's own SCR and neutral citations.
  - Every `Case Law Cited` entry: citations joined by ` : ` belong to the same case. They are merged with union-find, so an SCC citation in the text can resolve to a judgment we hold only under its SCR citation.
  - No fuzzy party-name matching (the spec forbids guessing).
- **Overruling language:** a regex over the citing paragraph (`overrul(e|ed|es|ing)`, `no longer good law`, `not good law`, `stands overruled`). It sets a flag only; the UI wording is fixed by the spec.

### 10. API and web
- **API endpoints (FastAPI + Pydantic):**
  - `GET /search`
  - `GET /judgments/{id}`
  - `GET /judgments/{id}/breakdown`
  - `POST /judgments/{id}/ask`
  - `GET /judgments/{id}/citations`
- **Input validation:** lengths (query ≤ 2,000, question ≤ 1,000), filter types and id format, all through Pydantic.
- **SQL:** parameterised only.
- **Rate limiting:** per-IP limiting in memory (slowapi), keyed on the client IP that Caddy forwards; the API trusts `X-Forwarded-For` only from Caddy on the internal Docker network.
- **Daily LLM cap:** a counter in Postgres (`llm_calls` per UTC day) checked before every LLM call. When it is exceeded, the endpoint returns a "busy" status that the UI renders. Cached breakdowns are still served.
- **CORS:** only the production Vercel origin and `http://localhost:3000`.
- **The browser calls the API host directly, not through a Vercel rewrite.** A rewrite would make every request arrive from Vercel's IPs, which breaks per-IP rate limiting.
- **Errors:** generic messages, with no stack traces in responses.
- **Web:**
  - Next.js pages: search, and a judgment view with headnotes, breakdown, Q&A, citations and paragraph anchors (`#p-<seq>`).
  - All model text is rendered as React text nodes; there is no `dangerouslySetInnerHTML`.
  - The research note lives in `localStorage` and is exported client-side as a `.md` Blob.
- **PDF link:** the public HTTPS S3 object URL.

### 11. Logging and privacy
- **Logs:** structured JSON logs with route, latency, result count and filter names only. Query and question text are never logged or stored (specs: judgment-search, answer-grounding).
- **What goes to Groq:** only paragraphs and the follow-up question; the UI tells the user next to the question box.

### 12. Deployment: Vercel + Oracle Always Free + Caddy
```
Browser ──https──► nyaya-search.vercel.app  (Next.js, Vercel free plan; no secrets)
   │
   └──https──► api.<free-subdomain>  (DuckDNS → server's public IP)
                 Oracle A1 server, Ubuntu (Arm64), Docker Compose:
                   caddy  :80/:443  automatic Let's Encrypt, HTTP→HTTPS, security headers
                   api    (FastAPI + models on CPU, non-root, read-only filesystem)  internal only
                   db     (ParadeDB, pinned tag)  internal only, persistent volume
                 OCI security list + host firewall: 22 (key only), 80, 443
Mac: pipeline (MPS) ──pg_dump -Fc──► scp ──► pg_restore on the server
Backups: nightly pg_dump → OCI Object Storage (Always Free), keep 7
Monitor: UptimeRobot (free) on /healthz every 5 min → email alert
```
- **Why Vercel for the web app:**
  - It is free, always on, has no cold start for static and edge pages, and gives a clean `*.vercel.app` link for the resume.
  - It keeps Next.js off the 12 GB server.
  - A custom domain can be added later without changing anything else.
- **Why Caddy instead of nginx + certbot:** it handles certificates and renewal by itself in a few lines of config, so there is less to break in a 2-day build.
- **Why ship a database dump:** ingestion and embedding need the Mac GPU, while the server only serves queries. The dump of 2024–25 is about 1–1.5 GB, and both machines run the same pinned ParadeDB image, so it restores cleanly.
- **Images:** built on the Mac for `linux/arm64`, which matches the server, and pushed to GHCR (free for public images) or copied with `docker save`.
- **Hardening:**
  - Containers run as non-root with `no-new-privileges` and memory limits: db about 5 GB, api about 4 GB.
  - SSH: password login and root login are disabled.
  - Unattended security upgrades are on.
- **Idle reclaim:** Oracle can reclaim Always Free servers that sit idle, and a demo with little traffic looks idle. Mitigation: upgrade the account to Pay-As-You-Go (Always Free resources stay free), confirmed against Oracle's current terms at sign-up. Set a ₹0 budget alert.
- **Fallback:** if no A1 capacity is available by the end of day 1, run the same Compose file on a Hetzner CAX21 (Arm64, 4 vCPU, 8 GB). Only the IP behind the DuckDNS name changes.

### 13. Evaluation
- **Query set:** `evals/queries.yaml` holds ≥ 20 hand-written fact-pattern queries with expected judgment ids and an `author` field.
- **Runner:** the runner calls the four `Retriever` setups, writes `evals/results/<timestamp>.json` and prints the table. It exits non-zero when hybrid+rerank recall@10 is below BM25.
- **Proxy set (optional):** "Issue for Consideration" → own judgment gives a large set for quick regression checks. It is labelled as a proxy and never quoted as the quality number, because the headnote shares wording with the judgment.

## Risks / Trade-offs

- **[2024+ only: thin citation graph]** Most cited judgments are older than the ingested years, so most citations stay unresolved and "cited by" counts are small. → Show unresolved citations as text. Stretch: load parquet metadata for every year as metadata-only judgments, so citations resolve to a title and PDF link.
- **[Paragraph numbering edge cases]** Quoted statutes with numbered clauses, or orders without numbering, break the N = previous + 1 rule. → The monotonic rule plus the derived-label fallback. Check by hand on 20 random PDFs and count anomalies in the ingest report.
- **[Reranker as support check]** A relevance score can pass a sentence that is related but not entailed. → A conservative threshold, a hand check of 10 answers, the visible machine-generated label and the research-aid note. Consider an NLI model later.
- **[Groq free-tier limits]** Tokens-per-minute caps can reject a full breakdown request. → The 8k context budget, caching, and the "temporarily unavailable" state. Switch `LLM_BASE_URL` to local Ollama for development.
- **[ParadeDB on arm64 / pg_search behaviour]** → Day-1 smoke test. Fallback to stock Postgres `tsvector` behind the same `Retriever` interface.
- **[Memory]** Postgres plus the two models plus Next dev plus Ollama on 16 GB. → Don't run Ollama while Groq is configured; keep Docker at about 4 GB for Postgres.
- **[Oracle sign-up or A1 capacity]** Card rejections (RuPay) and "out of capacity" can take days. → Start sign-up on day 1 with a Visa or Mastercard and retry other availability domains. Switch to the Hetzner fallback at the end of day 1.
- **[Oracle idle reclaim or limit changes]** → Upgrade to Pay-As-You-Go, keep nightly off-box backups, and keep the deploy fully scripted, so rebuilding on another server is about an hour.
- **[Search latency on CPU]** → Top-20, 256-token, int8 reranker; measured on the server. If it still misses, ship without the reranker (Decision 6).
- **[Public abuse burns the Groq quota]** → Per-IP limits plus the daily cap. Search does not depend on Groq, so the core feature keeps working.
- **[Free subdomain provider outage]** → The API hostname is in one Vercel env var. Moving to a paid domain later is a config change.
- **[2023 layout unknown]** Not checked. → Sample 2023 PDFs on day 1 and include the year only if it is Digital SCR.
- **[Breakdown truncation]** The context budget may leave out key paragraphs of long judgments. → Prioritise the paragraphs referenced by the reporter headnotes, which mark the holdings.

## Migration Plan

Greenfield.

- **Local:** `docker compose up -d db` → `pipeline sync --years 2024 2025` → `pipeline extract` → `pipeline index` → `pipeline citations` → `uv run api` → `npm run dev` in `web/`.
- **Production (first deploy):**
  1. Provision the A1 server, firewall and DuckDNS name.
  2. Install Docker.
  3. Copy `compose.prod.yml`, `Caddyfile` and `.env`.
  4. `pg_dump` on the Mac, then `pg_restore` on the server.
  5. `docker compose up -d`.
  6. Set `NEXT_PUBLIC_API_URL` in Vercel and deploy.
  7. Add the UptimeRobot check and the backup cron.
  8. Run the restore drill once.
- **Updates:**
  - Code: build and push images, then `docker compose pull && up -d`.
  - Data: dump and restore into a new database, then switch the API to it, so a bad load never replaces the live data.
- **Rollback:** redeploy the previous image tag. For data, point back to the previous database or restore the last backup.
