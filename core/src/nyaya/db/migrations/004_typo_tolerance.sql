-- Typo tolerance: corpus vocabulary for spelling suggestions, trigram matching for words and judge names.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

CREATE TABLE vocabulary (
    word text PRIMARY KEY,
    freq int  NOT NULL
);
CREATE INDEX vocabulary_trgm ON vocabulary USING gin (word gin_trgm_ops);
