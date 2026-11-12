-- Shared research notes: read-only links to a set of corpus paragraphs. Stores references only (judgment and ¶),
-- never user-supplied text. The owner token is random and only its hash is kept.
CREATE TABLE shared_notes (
    id                uuid PRIMARY KEY,
    items             jsonb NOT NULL,
    owner_token_hash  text NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    expires_at        timestamptz NOT NULL,
    revoked_at        timestamptz
);
