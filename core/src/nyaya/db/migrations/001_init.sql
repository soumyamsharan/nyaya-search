CREATE EXTENSION IF NOT EXISTS pg_search;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE judgments (
    id                text PRIMARY KEY,          -- dataset path, e.g. 2024_10_108_125
    year              int  NOT NULL,
    title             text NOT NULL,
    petitioner        text,
    respondent        text,
    decision_date     date,
    bench             text[] NOT NULL DEFAULT '{}',
    author            text,
    neutral_citation  text,
    scr_citation      text,
    disposal_nature   text,
    pdf_url           text NOT NULL,
    status            text NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'ok', 'scanned', 'failed')),
    status_reason     text,
    extractor_version int,
    pdf_sha256        text,
    updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX judgments_decision_date ON judgments (decision_date);

CREATE TABLE paragraphs (
    id            bigserial PRIMARY KEY,
    judgment_id   text NOT NULL REFERENCES judgments (id) ON DELETE CASCADE,
    seq           int  NOT NULL,
    opinion_idx   int  NOT NULL,
    label         text NOT NULL,
    label_derived boolean NOT NULL,
    text          text NOT NULL,
    embedding     halfvec(1024),
    UNIQUE (judgment_id, seq)
);
CREATE INDEX paragraphs_bm25 ON paragraphs USING bm25 (id, text) WITH (key_field = 'id');
CREATE INDEX paragraphs_embedding ON paragraphs USING hnsw (embedding halfvec_cosine_ops);

CREATE TABLE front_matter (
    judgment_id text NOT NULL REFERENCES judgments (id) ON DELETE CASCADE,
    section     text NOT NULL,
    text        text NOT NULL,
    PRIMARY KEY (judgment_id, section)
);

CREATE TABLE judgment_acts (
    judgment_id text NOT NULL REFERENCES judgments (id) ON DELETE CASCADE,
    act_norm    text NOT NULL,
    act_display text NOT NULL,
    section     text,
    UNIQUE NULLS NOT DISTINCT (judgment_id, act_norm, section)
);
CREATE INDEX judgment_acts_act ON judgment_acts (act_norm);

CREATE TABLE citation_aliases (
    citation_norm text PRIMARY KEY,
    judgment_id   text NOT NULL REFERENCES judgments (id) ON DELETE CASCADE
);

CREATE TABLE citations (
    id                  bigserial PRIMARY KEY,
    citing_judgment_id  text NOT NULL REFERENCES judgments (id) ON DELETE CASCADE,
    citing_seq          int  NOT NULL,
    raw                 text NOT NULL,
    citation_norm       text NOT NULL,
    cited_judgment_id   text REFERENCES judgments (id) ON DELETE SET NULL,
    overruling_language boolean NOT NULL DEFAULT false
);
CREATE INDEX citations_citing ON citations (citing_judgment_id);
CREATE INDEX citations_cited ON citations (cited_judgment_id);

CREATE TABLE breakdowns (
    judgment_id    text NOT NULL REFERENCES judgments (id) ON DELETE CASCADE,
    prompt_version text NOT NULL,
    model          text NOT NULL,
    content        jsonb NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (judgment_id, prompt_version, model)
);

-- Metadata only: never the user's question or query text.
CREATE TABLE llm_calls (
    id                bigserial PRIMARY KEY,
    ts                timestamptz NOT NULL DEFAULT now(),
    purpose           text NOT NULL,
    model             text NOT NULL,
    prompt_version    text NOT NULL,
    outcome           text NOT NULL,
    tokens_in         int,
    tokens_out        int,
    latency_ms        int,
    sentences_dropped int
);
CREATE INDEX llm_calls_ts ON llm_calls (ts);

CREATE TABLE ingest_runs (
    id          bigserial PRIMARY KEY,
    stage       text NOT NULL,
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    counts      jsonb NOT NULL DEFAULT '{}',
    outcome     text
);
