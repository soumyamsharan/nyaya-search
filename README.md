**Overview**

Nyaya Search helps lawyers find the right Supreme Court precedents from a description of their case's facts, and check in seconds that each one is still good law, with every point pinned to the paragraph it came from. Version 1 covers Supreme Court judgments only and runs entirely on open-source models.
The gap. Indian Kanoon is free but keyword-based, so finding the right precedent means many queries and a lot of reading. SCC Online and Manupatra are stronger but cost a lot, which puts them out of reach for many junior advocates and small chambers, especially outside metro High Courts.
Three things it does better:
1. Fact-pattern search: describe the facts and the legal issue in plain words; hybrid retrieval plus a reranker finds judgments with similar facts and issues, and says which paragraph matched and why.
2. Faster reading: a headnote-style breakdown of each judgment (facts, issues, held, ratio, key paragraphs), follow-up questions answered only from the text, and pinpoint citations ready to paste into a brief. Hindi output for district-court practitioners.
3. Is it still good law? A citation graph showing which later judgments followed, distinguished or overruled each judgment, with the treating paragraph as evidence.
Goals for the project:
• A working public demo used by real advocates and law students, with their feedback
• Measured quality: retrieval and faithfulness numbers that beat keyword search
• Production-grade engineering: pipelines, CI with eval gates, observability, Kubernetes deployment
