## Why

Indian advocates without SCC Online or Manupatra subscriptions research Supreme Court precedent on Indian Kanoon, which is keyword-only: finding an on-point judgment takes many queries and a lot of reading, and checking whether it still stands is manual. Nyaya Search lets a lawyer describe the facts in plain words, get similar judgments with the matching paragraph pinned, read a grounded breakdown, and see which later judgments cite it. This change builds the first working version in a 1–2 day sprint, cut down from the 9-week project plan to the parts that make the tool useful and trustworthy.

## What Changes

- Ingest recent Supreme Court judgments from the open AWS dataset (CC-BY-4.0): extract text, split each judgment into stably identified paragraphs, extract metadata, and index every paragraph for keyword and semantic search. Start with the recent years published in the clean Digital SCR format (2024 onward, about 800 judgments a year); older years use an OCR'd layout with margin letters and come later.
- Keep the law reporter's front matter (headnotes, case law cited, Acts, keywords) separate from the court's paragraphs, show it labelled as the reporter's, and use its parallel citations to resolve citations.
- Fact-pattern search: hybrid keyword + semantic retrieval with a reranker, returning judgments with their best-matching paragraph; phrase search, filters (year, judge, Act/section) and lookup by citation.
- Judgment reading: a headnote-style breakdown (facts, issues, held, ratio) where every line links to its paragraph, generated on first open and cached; follow-up questions answered only from the judgment's text with paragraph citations; link to the original PDF; Markdown research-note export.
- Answer grounding across all generated text: case names and citations come only from stored metadata, every generated sentence cites a paragraph that supports it or is removed, and the app says so when nothing relevant is found.
- Citation graph: extract and resolve citations between judgments, show "cites" and "cited by" with the citing paragraph, and surface overruling language in a citing paragraph as evidence (not as a verdict).
- A small evaluation suite (about 20 fact-pattern queries) that compares keyword, semantic, hybrid and hybrid+reranker retrieval, so quality claims are measured.
- A public, always-on website on a stable HTTPS link that anyone can open in a browser with no setup, suitable for a resume: the web app on Vercel, the API and database on an Oracle Cloud Always Free Arm server. Ingestion and embedding run on the developer's Mac and the finished database is shipped to the server.
- Protection for a public site: per-IP rate limits, a daily cap on LLM calls so strangers cannot exhaust the free quota, and search that keeps working when the LLM is unavailable.

Explicitly deferred from the project plan: embedding fine-tuning, Hindi and OCR, treatment labels beyond overruling language, key paragraphs ranked by citation count, logins and folders, Kubernetes, Grafana dashboards, advocate-sourced eval sets and the pilot. Terraform and a CI deploy pipeline are stretch goals.

## Capabilities

### New Capabilities

- `corpus-ingestion`: Acquiring Supreme Court judgments, extracting text, splitting them into stable numbered paragraphs, extracting metadata, indexing, and reporting ingestion quality.
- `judgment-search`: Fact-pattern, phrase and citation search over the corpus with filters, returning ranked judgments with the matching paragraph.
- `judgment-reading`: The judgment view: paragraph-linked breakdown, grounded follow-up Q&A, source PDF link and research-note export.
- `answer-grounding`: Cross-cutting rules for any generated text: no invented citations, sentence-level support checks, refusals, and what data leaves the machine.
- `citation-graph`: Extracting and resolving citations between judgments, cites/cited-by views with citing paragraphs, and flagging overruling language.
- `search-evaluation`: The retrieval eval set, metrics and the comparison report that backs quality claims.
- `public-access`: The public website: a stable HTTPS link, no setup for visitors, availability and responsiveness, abuse limits, and graceful degradation when the LLM is unavailable.

### Modified Capabilities

(none: no existing specs)

## Impact

- New monorepo layout: `pipeline/` (ingestion CLI), `core/` (search, rerank, grounding, citations), `api/` (HTTP API), `web/` (UI), `evals/`, `docker-compose.yml`.
- New dependencies: Postgres with vector and BM25 extensions, open embedding and reranker models (BGE-M3, bge-reranker-v2-m3) run locally, an LLM provider (Groq free tier; Ollama locally as fallback).
- Secrets: one LLM API key and the database password, kept in an untracked `.env` locally and only on the server in production; the web host holds no secrets.
- Hosting: an Oracle Cloud account (Always Free Arm server; sign-up needs a Visa or Mastercard and can hit "out of capacity"), a Vercel account, and a free uptime monitor. Fallback if Oracle capacity is unavailable: a small paid Arm server (Hetzner CAX21) running the identical deployment.
- Search must meet its latency target on the server's CPU, without a GPU, which constrains the reranker (see design.md).
- Disk: the corpus subset, model weights and indexes need roughly 20–40 GB locally.
- README is out of date (lists Hindi in version 1) and gets updated to the MVP scope.
