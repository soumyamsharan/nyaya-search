# Test scenarios: add-paragraph-roles-and-search-operators

Status: ✅ passed · ❌ failed · ⏳ not run yet.

## paragraph-roles

| ID | Scenario | Test | Status |
|---|---|---|---|
| PR-1 | Roles assigned during ingestion, counts reported | `pipeline roles`: all 71,635 paragraphs labelled. Latest run: reasoning 35,766 · facts 18,579 · precedent 7,798 · conclusion 3,231 · statute 2,124 · petitioner_argument 1,966 · respondent_argument 1,530 · issue 641 | ✅ |
| PR-2 | Deterministic | `test_roles::test_labelling_is_deterministic`; a re-run of the stage changes 0 rows when the rules are unchanged | ✅ |
| PR-3 | Counsel's submission → petitioner_argument | `test_roles::test_each_spec_cue_gets_its_role` | ✅ |
| PR-4 | Per contra / respondent → respondent_argument | `test_roles::test_each_spec_cue_gets_its_role`, `::test_unsided_counsel_submission_takes_the_last_side` | ✅ |
| PR-5 | Disposal at the end → conclusion | `test_roles::test_each_spec_cue_gets_its_role`, `::test_disposal_language_early_in_the_judgment_is_not_a_conclusion` | ✅ |
| PR-6 | Question for consideration → issue | `test_roles::test_each_spec_cue_gets_its_role`, `::test_issue_inside_a_precedent_discussion_is_precedent` | ✅ |
| PR-7 | Label visible with machine-assigned note | Browser check on 2024_1_604_622: role tag on every paragraph, plus the note "Paragraph roles are assigned automatically and may be wrong" | ✅ |
| PR-8 | Read only reasoning and conclusion | Browser check: chips → 16 of 25 paragraphs, original ¶ numbers kept, URL `?roles=reasoning,conclusion` | ✅ |
| PR-9 | Clear the filter | Browser check: "Show all" → 25 paragraphs, `roles` removed from the URL | ✅ |

**Rule accuracy (task 1.5)**

Each check used 40 random paragraphs, judged by hand. Rows of garbled table text were excluded.

| Rules version | Correct | Notes |
|---|---|---|
| First rules | 26/40 (65%) | Misses: early conclusions, precedent without a citation, arguments without a named side |
| Revised rules | 27/38 (71%) | Fresh sample |
| Final rules | 28/39 (72%) | Fresh sample |

- **What's reliable:** facts, court's reasoning, precedents and conclusions.
- **Weak spot:** arguments phrased without naming counsel or a side ("It is submitted that…", "Mr X submitted…").
- **Upgrade path:** design.md's pre-trained rhetorical-role model.

## search-query-language

| ID | Scenario | Test | Status |
|---|---|---|---|
| QL-1 | AND requires both terms | `test_text::test_boolean_operators`, `test_search::test_term_conditions_for_and_not`, `test_query_language_live::test_and_requires_both_terms` | ✅ |
| QL-2 | NOT excludes a term | `test_query_language_live::test_not_excludes_a_term`, browser check (`bail NOT anticipatory`: 10 results, none mention it) | ✅ |
| QL-3 | NOT with a phrase | `test_query_language_live::test_not_excludes_a_phrase` | ✅ |
| QL-4 | Lower-case words are not operators | `test_text::test_boolean_operators`, `test_query_language_live::test_lower_case_not_is_a_word` | ✅ |
| QL-5 | Only operators → error | `test_search::test_only_excluded_terms_is_rejected`, `test_query_language_live::test_only_excluded_terms_is_rejected` | ✅ |
| QL-6 | Match only in reasoning and conclusion | `test_query_language_live::test_search_within_reasoning_and_conclusion`, browser check | ✅ |
| QL-7 | Date range | `test_query_language_live::test_date_range` | ✅ |
| QL-8 | Author filter | `test_query_language_live::test_author_filter` | ✅ |
| QL-9 | Two judges on the bench | `test_query_language_live::test_bench_with_two_judges` | ✅ |
| QL-10 | Dismissed appeals only | `test_query_language_live::test_outcome_dismissed`, `test_search::test_new_filters_compile_to_parameters` | ✅ |
| QL-11 | Unknown role / bad date → 422 | `test_api::test_invalid_new_filters_are_422` | ✅ |
