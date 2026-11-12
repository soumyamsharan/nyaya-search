## Why

Lawyers start from a law, not only from a provision. The section page answers "what has the court said about Section
138?", but not "what has the court said about the Negotiable Instruments Act?" and the Act name is not clickable. There is
also no way to tell what an Act is, since the corpus records only its name.

## What Changes

- **Act page:** every judgment that refers to any section of an Act, newest first, with the sections each one refers to.
  Paginated (25 per page). Reached by clicking an Act name anywhere on the site.
- **About this Act:** a short description and the official source. For the most-cited Acts (about 30) a plain-language
  description is written and reviewed by hand. Every Act page links to its official entry on India Code.
- Section titles are not part of this change.

## Capabilities

### New Capabilities

- `act-pages`: the Act page, the About section, and the link from Act names.

## Impact

- API: `GET /v1/statutes/{key}` (Act name, judgment count, judgments with the sections each refers to; paginated).
- Data: a small curated file `core/src/nyaya/data/acts.yaml` with the description, the reviewer, and the source URL for each
  curated Act. Acts not in the file show the name and the India Code link only.
- Web: `/statutes/{key}` page; Act names in the index and in judgment text link to it.
- Source: India Code. Its URL format and terms of use must be confirmed before links are published.
