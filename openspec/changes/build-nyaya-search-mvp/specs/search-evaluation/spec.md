## Purpose

Measures retrieval quality on a fixed set of fact-pattern queries so that every quality claim about Nyaya Search comes from a repeatable number, not an impression.

## ADDED Requirements

### Requirement: Eval query set
The project SHALL keep a version-controlled set of at least 20 fact-pattern queries, each with one or more judgments a lawyer would cite for it, all present in the corpus. Each entry SHALL record who wrote or checked it.

#### Scenario: Invalid entry
- **WHEN** an eval entry names a judgment that is not in the corpus
- **THEN** the eval run reports the entry as invalid and excludes it from metrics

### Requirement: Retrieval comparison
The eval run SHALL compute recall@10 and MRR for four setups on the same queries: keyword only, semantic only, hybrid, and hybrid with reranker, and SHALL report p95 latency for each.

#### Scenario: Comparison table
- **WHEN** the eval suite runs
- **THEN** it outputs a table with recall@10, MRR and p95 latency for all four setups

### Requirement: Saved results
Each eval run SHALL save its results as a JSON file with a timestamp and the configuration used, so runs can be compared.

#### Scenario: Two runs compared
- **WHEN** the eval suite has run twice
- **THEN** both result files exist and record their configurations

### Requirement: Quality gate
The eval run SHALL exit with a failure status when hybrid-with-reranker recall@10 is below keyword-only recall@10.

#### Scenario: Gate fails
- **WHEN** hybrid-with-reranker recall@10 is lower than keyword-only
- **THEN** the run exits non-zero and names the gate that failed
