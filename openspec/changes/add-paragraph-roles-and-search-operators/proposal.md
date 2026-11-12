## Why

Supreme Court judgments run to dozens of paragraphs, and lawyers mostly need the court's own reasoning and its conclusion, not every argument it recorded. A match inside a rejected argument is not the law. Power users also expect precise keyword control and filters they know from Indian Kanoon. This change adds both on top of the MVP (`build-nyaya-search-mvp`).

## What Changes

- **Paragraph role labels:** every paragraph is labelled once during ingestion with the job it does in the judgment: Facts, Issue, Petitioner's argument, Respondent's argument, Statute, Precedent, Court's reasoning or Conclusion. Labels come from transparent cue-phrase and position rules, and are shown as machine-assigned.
- **Reading by role:** the judgment page shows each paragraph's label, and a filter can hide every paragraph except the chosen roles (e.g. only reasoning and conclusion).
- **Search by role:** search can be limited to paragraphs with chosen roles, e.g. match only in the court's reasoning and conclusion.
- **Search operators:** `AND` (both terms must appear), `OR` (either term), and `NOT` (exclude a term) in upper case, alongside the existing quoted phrases.
- **New filters:** exact decision-date range, author judge, several judges who must all be on the bench, and outcome (allowed, partly allowed, dismissed, disposed of, other).
- **No court filter yet:** the corpus has only the Supreme Court. The filter is added once High Courts are.

## Capabilities

### New Capabilities

- `paragraph-roles`: Assigning a role label to every paragraph, showing labels, and filtering a judgment by role.
- `search-query-language`: Boolean operators, role-restricted search, and the date, author, bench and outcome filters.

### Modified Capabilities

(none: the MVP's capabilities are not archived yet; these are separate capabilities)

## Impact

- **Database:** a `role` column on paragraphs (migration 003), and a `pipeline roles` stage that fills it. The stage takes seconds and needs no model or network.
- **API:** `GET /v1/search` gets new parameters (`date_from`, `date_to`, `author`, repeatable `judge`, `outcome`, repeatable `role`), and paragraphs in `GET /v1/judgments/{id}` carry `role`.
- **Web:** new filter fields and an operators hint on the search page, plus role tags and a role filter on the judgment page.
- **Upgrade path:** an open pre-trained rhetorical-role model for Indian judgments (SemEval-2023 / OpenNyAI) can replace the rules later if it measurably beats them. That is out of scope here.
