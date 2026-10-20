-- C3B2B disposable-only additive rehearsal. Not in production Alembic chain.
-- Caller verifies exact DB/user/marker before executing. No existing table ALTER.
CREATE TABLE customized_candidate_schema (version integer PRIMARY KEY CHECK(version=1));
INSERT INTO customized_candidate_schema VALUES (1);
CREATE TABLE customized_candidate_sessions (
    session_id uuid PRIMARY KEY,
    subject varchar NOT NULL REFERENCES users(id),
    credential_fingerprint varchar(64) NOT NULL UNIQUE,
    credential_digest varchar(64) NOT NULL,
    revision integer NOT NULL CHECK(revision>0),
    entitlement_reference varchar NOT NULL,
    scopes jsonb NOT NULL,
    valid_from timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK(expires_at>valid_from),
    revoked boolean NOT NULL DEFAULT false,
    UNIQUE(subject,session_id)
);
CREATE TABLE customized_candidate_events (
    subject varchar NOT NULL REFERENCES users(id),
    proposal_id varchar NOT NULL,
    revision integer NOT NULL CHECK(revision>0),
    document jsonb NOT NULL,
    previous_digest varchar(64) NOT NULL,
    digest varchar(64) NOT NULL,
    PRIMARY KEY(subject,proposal_id,revision)
);
CREATE TABLE customized_candidate_heads (
    subject varchar NOT NULL,
    proposal_id varchar NOT NULL,
    revision integer NOT NULL CHECK(revision>0),
    digest varchar(64) NOT NULL,
    PRIMARY KEY(subject,proposal_id),
    FOREIGN KEY(subject,proposal_id,revision) REFERENCES customized_candidate_events(subject,proposal_id,revision)
);
CREATE TABLE customized_candidate_commands (
    subject varchar NOT NULL REFERENCES users(id),
    request_key varchar(96) NOT NULL,
    digest varchar(64) NOT NULL,
    response jsonb NOT NULL,
    PRIMARY KEY(subject,request_key)
);
-- Receipt and full consent audit are embedded in immutable event JSON, avoiding
-- a second consent-state model. Runtime privileges/retention require release review.
