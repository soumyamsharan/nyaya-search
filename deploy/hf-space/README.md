---
title: Nyaya Search API
emoji: ⚖️
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Fact-pattern search over Supreme Court of India judgments
---

# Nyaya Search API

Backend for Nyaya Search: fact-pattern search over Supreme Court of India judgments (2024 onwards), with every
result, summary line and answer pinned to the paragraph it came from.

- Health: `/healthz`
- API docs: `/docs`
- Search: `/v1/search?q=...`

Judgments come from the Indian Supreme Court Judgments open dataset (CC-BY-4.0). Credit to its maintainers.
Generated summaries and answers are research aids; read the judgment before citing it.

Built from https://github.com/soumyamsharan/nyaya-search with `scripts/publish-hf-space.sh`.
