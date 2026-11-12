-- Every statute reference in a paragraph, of every kind (section, article, rule, regulation, notification).
CREATE TABLE statute_refs (
    id           bigserial PRIMARY KEY,
    judgment_id  text NOT NULL REFERENCES judgments (id) ON DELETE CASCADE,
    seq          int  NOT NULL,
    kind         text NOT NULL,
    key          text NOT NULL,
    name         text NOT NULL,
    number       text NOT NULL,
    slug         text NOT NULL,
    raw          text NOT NULL
);
CREATE INDEX statute_refs_provision ON statute_refs (kind, key, slug);
CREATE INDEX statute_refs_judgment ON statute_refs (judgment_id);
