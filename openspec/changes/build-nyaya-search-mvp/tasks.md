## 1. Start now (accounts with lead time)

- [ ] 1.1 Sign up for Oracle Cloud with a Visa or Mastercard and choose a home region; request an Ampere A1 server (Ubuntu, Arm64, max Always Free shape), retrying other availability domains if "out of capacity"; record the confirmed OCPU/RAM limits
- [ ] 1.2 Upgrade the Oracle account to Pay-As-You-Go if current terms still exempt it from idle reclaim, and set a ₹0 budget alert
- [ ] 1.3 Create Groq, Vercel, DuckDNS and UptimeRobot accounts; reserve the DuckDNS subdomain for the API
- [ ] 1.4 Decision point at end of day 1: if no A1 server is running, provision a Hetzner CAX21 instead and note it in design.md

## 2. Setup and smoke tests

- [x] 2.1 Create the monorepo skeleton (`core/`, `pipeline/`, `api/`, `evals/`, `web/`) as a uv workspace on Python 3.12, with `.gitignore` (including `.env`, `data/`, model caches) and `.env.example` (DB URL, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_DAILY_CAP`, allowed web origins)
- [x] 2.2 Add `docker-compose.yml` with a pinned ParadeDB image, port bound to 127.0.0.1, password from `.env`, named volume; verify `pg_search` and `vector` extensions load on arm64 (fall back to stock Postgres `tsvector` if not, and note it in design.md)
- [x] 2.3 Write schema migrations for the tables in design.md §3, including the BM25 index on `paragraphs.text` and the HNSW index on `paragraphs.embedding`
- [x] 2.4 Download BGE-M3 and bge-reranker-v2-m3; confirm both run on MPS and record embedding throughput (paragraphs/second)
- [x] 2.5 Sample 5 PDFs from 2023 and record whether they use the Digital SCR layout; set the ingest year list accordingly

## 3. Ingestion pipeline (corpus-ingestion)

- [x] 3.1 `pipeline sync --years …`: incremental download of PDFs and the year's metadata parquet with `--no-sign-request`
- [x] 3.2 Load parquet metadata into `judgments` (title, parties, date parsed from DD-MM-YYYY, SCR and neutral citations, `pdf_url`)
- [x] 3.3 Span-level text extraction that drops running headers, page numbers, footnote blocks and superscript markers; flag scanned PDFs
- [x] 3.4 Split front matter on Digital SCR section labels into `front_matter`; parse bench and author from the `[… JJ.]` line; parse `List of Acts` and section references into `judgment_acts`
- [x] 3.5 Paragraph splitter: monotonic `N.` rule, new opinion on reset after an author line, opinion-aware labels, derived-label fallback; stamp `extractor_version`
- [x] 3.6 Unit tests for the splitter: numbered judgment, restarted numbering in a concurring opinion, numbered clauses inside a quotation, unnumbered order, and re-running gives identical output
- [x] 3.7 Per-judgment error isolation, and an ingest report (processed / failed / scanned / duplicates / empty paragraphs) saved to `ingest_runs`, with non-zero exit above the failure threshold
- [ ] 3.8 `pipeline index`: embed paragraphs on MPS in batches, write `halfvec` embeddings, skip already-embedded paragraphs
- [ ] 3.9 Run sync → extract → index for the chosen years; check 20 random judgments by hand against their PDFs and fix anomalies

## 4. Search (judgment-search)

- [x] 4.1 `Retriever` interface with BM25, vector, hybrid (RRF k=60) and hybrid+rerank implementations, all applying year, judge and Act/section filters
- [x] 4.2 Best-paragraph-per-judgment grouping, configurable rerank depth and truncation, top-10 output with the matched paragraph and label
- [ ] 4.3 Reranker backends: full-precision (MPS) for dev and an int8 ONNX export for CPU, selected by config
- [x] 4.4 Quoted-phrase handling on both the BM25 and vector sides
- [x] 4.5 Citation query detection and lookup through `citation_aliases`, with a "not in corpus" response
- [x] 4.6 Relevance threshold producing "no relevant judgments found"
- [x] 4.7 Input validation (empty query, 2,000-char limit) and tests for each search scenario in the spec

## 5. Evaluation (search-evaluation)

- [x] 5.1 Write `evals/queries.yaml` with at least 20 fact-pattern queries and expected judgment ids from the ingested years, each with an `author` (written by the developer; ask a practising advocate to check if possible)
- [ ] 5.2 Eval runner: validate entries against the corpus, compute recall@10, MRR and p95 latency for the four setups, accept an API base URL so it can run against local or production, write `evals/results/<timestamp>.json`, print the table, and exit non-zero if hybrid+rerank recall@10 < BM25
- [ ] 5.3 Run the evals locally, tune RRF and the relevance threshold, and compare rerank depth 20 vs 50 and int8 vs full precision for recall

## 6. Citation graph (citation-graph)

- [x] 6.1 Citation regexes (SCC, SCR incl. Supp., AIR SC, INSC) with normalisation, plus tests on real strings from the corpus
- [x] 6.2 Build `citation_aliases` from each judgment's own citations and from `Case Law Cited` parallel citations (union-find)
- [x] 6.3 `pipeline citations`: extract citations from every paragraph, resolve via aliases, keep unresolved ones as text, set the overruling-language flag
- [x] 6.4 Report resolution rate in the ingest report

## 7. LLM and grounding (answer-grounding)

- [x] 7.1 OpenAI-compatible LLM client reading `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`, with timeout, one retry, 429 → busy, and metadata-only logging to `llm_calls`
- [x] 7.2 Daily LLM cap checked before each call (`LLM_DAILY_CAP`), returning the busy state when exceeded
- [x] 7.3 Grounding filter: drop sentences with missing or out-of-context paragraph refs, or with case names or citations not in the supplied paragraphs
- [x] 7.4 Reranker-based support check with `SUPPORT_THRESHOLD`; "no supported answer" when nothing survives; record dropped counts
- [x] 7.5 Tests: uncited sentence, foreign paragraph id, invented citation, unsupported claim, all-dropped and cap-reached cases

## 8. Reading features and API (judgment-reading)

- [x] 8.1 FastAPI app: models loaded once at startup, `/healthz`, CORS limited to the configured origins, per-IP rate limiting on the forwarded client IP (trusted only from Caddy), generic error responses, no query or question text in logs
- [x] 8.2 `GET /search` and `GET /judgments/{id}` (metadata, paragraphs with labels and the derived flag, reporter front matter with `[Para N]` links, PDF URL)
- [x] 8.3 `GET /judgments/{id}/breakdown`: paragraph selection within the 8k budget, structured generation, grounding, cache per prompt version and model, cached result still served when busy, and the busy and unavailable states
- [x] 8.4 `POST /judgments/{id}/ask`: 1,000-char limit, in-judgment retrieval of the top 8 paragraphs, grounded answer, refusal or busy state
- [x] 8.5 `GET /judgments/{id}/citations`: cites and cited-by with citing paragraphs, unresolved citations as text, overruling-language evidence

## 9. Web UI

- [x] 9.1 Next.js + TypeScript + Tailwind app with `NEXT_PUBLIC_API_URL`, and a footer with dataset attribution (CC-BY-4.0)
- [x] 9.2 Search page: query box, filters, results with matched paragraph, label, cited-by count and a link to `#p-<seq>`
- [x] 9.3 Judgment page: metadata, the reporter headnotes section (labelled), paragraphs with anchors and highlight, the derived-numbering notice, and the PDF link
- [x] 9.4 Breakdown and Q&A panels: paragraph-linked sentences rendered as text, the machine-generated label and research-aid note, the external-provider notice by the question box, and the unavailable, busy and no-answer states
- [x] 9.5 Citations panel: cites and cited-by lists, and the overruling-language notice worded as evidence only
- [x] 9.6 Copy pinpoint citation per paragraph; research-note collection in localStorage with Markdown export and an empty-note message
- [x] 9.7 "Service temporarily unavailable" page when the API cannot be reached

## 10. Deployment (public-access)

- [ ] 10.1 API Dockerfile: Arm64, Python 3.12 slim, non-root user, models baked in or downloaded to a volume at first start, read-only root filesystem
- [x] 10.2 `compose.prod.yml` (caddy, api, db) with internal network, only Caddy publishing 80/443, memory limits, `no-new-privileges`, restart policies; `Caddyfile` with the DuckDNS hostname, HTTPS redirect and security headers
- [ ] 10.3 Harden the server: OCI security list and host firewall allow only 22/80/443, key-only SSH with root and password login disabled, unattended security upgrades, Docker installed
- [ ] 10.4 Point the DuckDNS name at the server's public IP and confirm Caddy obtains a certificate
- [ ] 10.5 Build the arm64 API image on the Mac and ship it (GHCR or `docker save`); `scripts/ship-db.sh` to `pg_dump -Fc` on the Mac, copy over and `pg_restore` into a fresh database on the server
- [ ] 10.6 Start the production stack, check `/healthz` and a sample search over HTTPS
- [ ] 10.7 Run the eval suite against the production API; if p95 ≥ 3 s, lower rerank depth or disable the reranker per design Decision 6 and record the outcome
- [ ] 10.8 Create the Vercel project from `web/`, set `NEXT_PUBLIC_API_URL`, deploy, and add the Vercel origin to the API's allowed origins
- [ ] 10.9 Nightly backup cron: `pg_dump` to OCI Object Storage, keeping 7; run one restore drill and record it
- [ ] 10.10 UptimeRobot check on `/healthz` every 5 minutes with email alerts
- [ ] 10.11 Public-access checks: open the link on another laptop and on a phone on mobile data; confirm HTTP redirects to HTTPS; scan the server and see only 22/80/443 open; search the web bundle for secrets; exhaust a low test cap and confirm search still works

## 11. Wrap-up

- [ ] 11.1 Update README: the live link, MVP scope (remove Hindi from v1), architecture diagram, local setup and deploy steps, eval table with production latency, attribution, limitations (2024+ only; overruling language is not a verdict)
- [ ] 11.2 Run `openspec validate build-nyaya-search-mvp --strict` and tick off spec scenarios covered by tests

## 12. Stretch (only if time remains)

- [ ] 12.1 Load parquet metadata for all years as metadata-only judgments so older citations resolve to a title and PDF link
- [ ] 12.2 Proxy eval set from "Issue for Consideration" → own judgment, labelled as a proxy
- [ ] 12.3 Terraform (OCI provider) for the server, network, security list and object storage bucket
- [ ] 12.4 GitHub Actions: lint, tests and evals on PRs; build the arm64 image and deploy over SSH on merge to main
- [ ] 12.5 Custom domain for the web app and API
