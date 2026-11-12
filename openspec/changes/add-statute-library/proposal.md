## Why

Judgments refer to many kinds of law: Acts (1,405 judgments), Constitution articles (788), Rules (420), Regulations (51) and
Notifications or Ordinances (59). We capture only Acts today. Lawyers need every kind, each linked to its official source.

## What Changes

- **Constitution:** one entry for the Constitution of India, and an article page for each article referred to, listing the
  judgments that refer to it.
- **Rules:** each Rule is shown under its parent Act (for example Order XII Rule 6 under the Code of Civil Procedure), with
  the judgments that refer to it.
- **Regulations and Notifications:** listed with the judgments that refer to them.
- **Official source for everything:** every statute page links to India Code's search for that name, so the official text
  is one click away. No India Code IDs are collected automatically.
- **Descriptions:** short descriptions only for the curated Acts, reviewed by a person before publication.

## Limits

- India Code's policy prohibits automated scraping. Links therefore use India Code's search page for each name, not item
  IDs. This keeps us within the policy, at the cost of one extra click for the official text.
- Descriptions are not written for every statute: thousands of entries cannot be reviewed by hand. Only the curated list has
  one.

## Capabilities

### New Capabilities

- `statute-library`: all statute kinds, grouped under their parent where one exists, with official search links.

## Impact

- Extraction: article, rule, regulation and notification references from paragraph text (the Act extractor already works this way).
- Data: `statute_refs` rows per kind, with the parent Act where it can be determined.
- API: `GET /v1/statutes` gains the kinds; new endpoints for articles, rules, regulations and notifications.
- Web: a page per kind; the official India Code search link on every page.
