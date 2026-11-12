# Test scenarios: build-nyaya-search-mvp

Every spec scenario maps to at least one automated test or a recorded manual check.
Status: ✅ passed · ❌ failed · ⏳ not run yet · 🚫 blocked (needs something outside this machine).

## Setup (done before testing)

| Step | Command / state | Status |
|---|---|---|
| Python 3.12 workspace and dependencies | `uv sync` | ✅ |
| Local Postgres (ParadeDB 0.26.6-pg17) with pg_search + pgvector | `docker compose up -d db` | ✅ |
| Schema migrated | `uv run pipeline migrate` | ✅ |
| Corpus 2024–2026 downloaded and loaded (1,920 judgments) | `uv run pipeline sync` | ✅ |
| Text and paragraphs extracted (71,635 paragraphs, 0 failures) | `uv run pipeline extract` | ✅ |
| Embedding and reranker models downloaded to `models/` (parallel ranges via the proxy; SHA-256 verified against Hugging Face) | small files via `hf download --local-dir`, weights via ranged `curl` | ✅ |
| Paragraph embeddings | `uv run pipeline index` | ⏳ |
| Citation graph built (8,221 citations, 400 resolved in corpus, 4,343 aliases) | `uv run pipeline citations` | ✅ |
| Local LLM in place of Groq | Ollama `qwen2.5:7b` | ✅ |
| Web app dependencies (Node 22; Tailwind pinned to 4.3.3, see notes) | `npm install` in `web/` | ✅ |
| Web production build | `npm run build` | ✅ |

How to run: unit tests `uv run pytest`; integration tests `uv run pytest -m integration`; evals `uv run evals`.

## corpus-ingestion

| ID | Scenario | Test | Status |
|---|---|---|---|
| CI-1 | Sync a year range | `pipeline sync` for 2024–2026: only those years fetched (data/pdf/2024..2026) | ✅ |
| CI-2 | Re-run is incremental | second `pipeline sync` downloads nothing (aws s3 sync) | ⏳ |
| CI-3 | Numbered paragraphs keep their printed numbers | `test_parsing::test_numbered_paragraphs_keep_printed_numbers`, `::test_real_pdf_paragraphs_front_matter_and_page_furniture` | ✅ |
| CI-4 | Numbering restarts in a separate opinion | `test_parsing::test_restarted_numbering_in_a_separate_opinion_gets_unique_labels` | ✅ |
| CI-5 | Unnumbered judgment → derived labels, marked | `test_parsing::test_unnumbered_order_gets_derived_labels`, `test_reading_live::test_derived_numbering_is_flagged` | ⏳ |
| CI-6 | Re-ingestion is deterministic | `test_parsing::test_re_parsing_is_deterministic`, `test_pipeline_live::test_re_ingestion_keeps_paragraph_ids_labels_text_and_embeddings` | ✅ |
| CI-7 | Page furniture removed | `test_parsing::test_real_pdf_paragraphs_front_matter_and_page_furniture` | ✅ |
| CI-8 | Digital SCR headnotes stored as reporter front matter | `test_parsing::test_front_matter_is_kept_separate_from_paragraphs` | ✅ |
| CI-9 | Case law cited captured | `test_pipeline_live::test_reporter_case_law_cited_is_stored` | ✅ |
| CI-10 | Metadata available for filtering | `test_search_live::test_year_filter`, `::test_judge_filter`, `::test_act_and_section_filter` | ⏳ |
| CI-11 | Unknown field stays empty | metadata loader writes NULL for unparsable dates/citations (`_parse_date`, `_citation_text`) | ⏳ |
| CI-12 | Scanned judgment flagged | `test_parsing::test_blank_pdf_looks_scanned` | ✅ |
| CI-13 | One bad PDF isolated | `test_pipeline_live::test_one_corrupt_pdf_is_isolated_and_reported` | ✅ |
| CI-14 | Run summary saved | `test_pipeline_live::test_ingest_runs_are_recorded` | ✅ |
| CI-15 | Too many failures → non-zero exit | `test_pipeline_and_evals::test_run_report_fails_above_threshold` | ✅ |
| CI-16 | Attribution visible | UI check: footer on every page | ✅ |

## judgment-search

| ID | Scenario | Test | Status |
|---|---|---|---|
| JS-1 | Plain-language query → up to 10 distinct judgments | `test_search_live::test_fact_pattern_search_returns_distinct_judgments_with_matched_paragraph`, `test_search::test_fact_pattern_search_reranks_and_returns_matched_paragraph` | ⏳ |
| JS-2 | Query too long rejected | `test_api::test_search_validation_errors_use_the_error_format` | ✅ |
| JS-3 | Empty query rejected | `test_api::test_search_validation_errors_use_the_error_format`, UI check | ✅ |
| JS-4 | Result shows matched paragraph and label | `test_search_live::test_fact_pattern_search_returns_distinct_judgments_with_matched_paragraph` | ⏳ |
| JS-5 | Jump to paragraph, highlighted | UI check: result ¶ link opens judgment scrolled to `#p-<seq>` and highlighted | ✅ |
| JS-6 | Quoted phrase | `test_search_live::test_phrase_search_requires_the_exact_phrase`, `test_text::test_quoted_phrases_are_split_from_free_text` | ⏳ |
| JS-7 | Year filter | `test_search_live::test_year_filter` | ⏳ |
| JS-8 | Act and section filter | `test_search_live::test_act_and_section_filter`, `test_search::test_filters_are_parameterised_not_interpolated` | ⏳ |
| JS-9 | Known citation → only that judgment | `test_search_live::test_search_by_known_citation_returns_only_that_judgment`, `test_search::test_citation_query_returns_only_that_judgment` | ⏳ |
| JS-10 | Citation not in corpus | `test_search_live::test_citation_not_in_corpus`, `test_search::test_citation_not_in_corpus_says_so` | ⏳ |
| JS-11 | Off-topic query → "no relevant judgments" | `test_search_live::test_off_topic_query_says_nothing_relevant`, `test_search::test_no_relevant_results_gives_a_message` | ⏳ |
| JS-12 | p95 latency < 3 s | `test_search_live::test_search_p95_latency_under_3_seconds` (local); production: task 10.7 | ⏳ |
| JS-13 | Query not persisted | `test_search_live::test_search_text_is_not_stored`, `test_api::test_query_and_question_text_never_logged` | ⏳ |
| JS-14 | Burst of requests → 429 | `test_api::test_rate_limit_returns_429_but_health_is_exempt` | ✅ |

## judgment-reading

| ID | Scenario | Test | Status |
|---|---|---|---|
| JR-1 | Open a judgment: metadata and labelled paragraphs | `test_reading_live::test_judgment_view_has_labelled_paragraphs_front_matter_and_pdf` | ⏳ |
| JR-2 | Derived numbering labelled | `test_reading_live::test_derived_numbering_is_flagged`, UI check | ⏳ |
| JR-3 | Reporter headnotes shown with [Para N] links | UI check | ⏳ |
| JR-4 | Breakdown first request: generated, stored, every line linked | `test_reading_live::test_breakdown_lines_cite_real_paragraphs_and_are_cached`, `test_reading::test_breakdown_is_generated_grounded_and_cached` | ⏳ |
| JR-5 | Cached breakdown, no model call | `test_reading_live::test_breakdown_lines_cite_real_paragraphs_and_are_cached` | ⏳ |
| JR-6 | Generation unavailable → message, nothing partial | `test_reading::test_breakdown_with_nothing_supported_is_unavailable_not_partial`, `test_api::test_breakdown_busy_and_unavailable_are_503` | ⏳ |
| JR-7 | Answerable question cites paragraphs | `test_reading_live::test_answerable_question_cites_paragraphs`, `test_reading::test_question_answered_with_paragraph_citations_and_scoped_to_judgment` | ⏳ |
| JR-8 | Question the judgment does not answer | `test_reading_live::test_unrelated_question_is_refused`, `test_reading::test_question_not_addressed` | ⏳ |
| JR-9 | Original PDF link | `test_reading_live::test_judgment_view_has_labelled_paragraphs_front_matter_and_pdf`, UI check | ✅ |
| JR-10 | Copy a paragraph with its citation | UI check | ✅ |
| JR-11 | Export a research note | UI check | ✅ |
| JR-12 | Export with nothing collected | UI check | ✅ |

## answer-grounding

| ID | Scenario | Test | Status |
|---|---|---|---|
| AG-1 | Model mentions an outside case → dropped | `test_grounding::test_invented_case_name_is_dropped`, `::test_invented_citation_is_dropped` | ✅ |
| AG-2 | Uncited sentence dropped | `test_grounding::test_uncited_sentence_is_dropped` | ✅ |
| AG-3 | Reference to a paragraph not supplied dropped | `test_grounding::test_sentence_citing_a_paragraph_not_supplied_is_dropped` | ✅ |
| AG-4 | Unsupported claim dropped | `test_grounding::test_unsupported_claim_is_dropped` | ✅ |
| AG-5 | Everything removed → "no supported answer" | `test_reading::test_answer_with_every_sentence_dropped_says_no_supported_answer` | ✅ |
| AG-6 | Machine-generated label and research-aid note | UI check | ⏳ |
| AG-7 | Question box notice about external provider | UI check | ✅ |
| AG-8 | Question not persisted | `test_reading_live::test_answerable_question_cites_paragraphs`, `test_llm::test_successful_call_logs_metadata_only`, `test_api::test_query_and_question_text_never_logged` | ⏳ |
| AG-9 | Markup in model output shown as text | React renders text nodes only (no `dangerouslySetInnerHTML` in `web/src`) | ✅ |

## citation-graph

| ID | Scenario | Test | Status |
|---|---|---|---|
| CG-1 | Reported citation in a paragraph recorded | `test_text::test_citation_formats_normalise`, `::test_parallel_citations_found_in_order` | ✅ |
| CG-2 | Resolvable citation linked | `test_reading_live::test_citation_graph_shape_and_cited_by` | ⏳ |
| CG-3 | Resolved through a parallel citation | `test_pipeline_and_evals::test_parallel_citation_resolves_through_case_law_cited` | ✅ |
| CG-4 | Unresolvable citation shown as text, no guess | `test_reading_live::test_unresolved_citations_are_listed_as_text`, `test_pipeline_and_evals::test_ambiguous_alias_group_is_not_guessed` | ⏳ |
| CG-5 | Cited-by list with citing paragraph | `test_reading_live::test_citation_graph_shape_and_cited_by` | ⏳ |
| CG-6 | Cited-by count on search results | `test_reading_live::test_citation_graph_shape_and_cited_by` | ⏳ |
| CG-7 | Overruling language found → evidence notice | `test_reading_live::test_overruling_language_is_evidence_not_verdict`, `test_text::test_overruling_language` | ⏳ |
| CG-8 | No overruling language → no notice, no "good law" claim | UI check | ✅ |
| CG-9 | Notice wording never says "overruled" as a verdict | UI check | ⏳ |

## search-evaluation

| ID | Scenario | Test | Status |
|---|---|---|---|
| SE-1 | Invalid eval entry reported and excluded | evals run with a deliberately invalid entry | ⏳ |
| SE-2 | Comparison table for four setups | `uv run evals` | ⏳ |
| SE-3 | Results saved with configuration | `evals/results/*.json` | ⏳ |
| SE-4 | Gate fails when hybrid+rerank < BM25 | `test_pipeline_and_evals::test_eval_gate` | ✅ |

## public-access

| ID | Scenario | Test | Status |
|---|---|---|---|
| PA-1 | First-time visitor, no setup | production link on another laptop (task 10.11) | 🚫 needs Oracle server + Vercel |
| PA-2 | Redeploy keeps the link | production | 🚫 needs Oracle server + Vercel |
| PA-3 | HTTP redirected to HTTPS | local production stack: `curl -I http://localhost` → 308 to https | ⏳ |
| PA-4 | No cold start | production (Vercel + always-on server) | 🚫 needs Oracle server + Vercel |
| PA-5 | Works with developer laptop off | production | 🚫 needs Oracle server + Vercel |
| PA-6 | Only 80/443 (+SSH) reachable | local production stack publishes only Caddy ports; server firewall in `scripts/server-setup.sh` | ⏳ |
| PA-7 | No secrets in the web app | grep of the built web bundle for keys | ⏳ |
| PA-8 | Daily cap reached → AI busy, search works | `test_reading_live::test_daily_cap_blocks_ai_but_search_and_cache_still_work`, `test_llm::test_daily_cap_blocks_the_call_and_records_it` | ⏳ |
| PA-9 | Cached breakdown after cap | `test_reading_live::test_daily_cap_blocks_ai_but_search_and_cache_still_work` | ⏳ |
| PA-10 | API down → friendly unavailable page | UI check with the API stopped | ⏳ |
| PA-11 | Health alert when down | UptimeRobot on production | 🚫 needs Oracle server |
| PA-12 | Restore drill | `scripts/restore-drill.sh` against the local database | ⏳ |

## Results log

(filled in as test runs complete)
