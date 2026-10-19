"""Persist existing Customized proposal/session contracts; additive, no backfill."""
from alembic import op
revision = '0022_customized_application'
down_revision = '0021_selected_workout_dates'
branch_labels = None
depends_on = None

def upgrade():
    op.execute(SCHEMA)
    op.execute(INDEXES)

def downgrade():
    raise RuntimeError('Retain consent/program history; use a data-preserving forward migration')

SCHEMA = r"""
-- Application schema, first rehearsed on a verified disposable target.
-- No existing table ALTER or historical consent inference.
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

"""

INDEXES = r"""
-- Source-read indexes qualified on disposable PostgreSQL before release.
-- Existing snapshot/state and supersedes indexes are reused where sufficient.
CREATE INDEX ix_c3b2b_plan_user_week_id ON workout_plans(user_id,week_start,id);
CREATE INDEX ix_c3b2b_occ_user_week ON workout_occurrences(user_id,week_start);
CREATE INDEX ix_c3b2b_occ_user_date ON workout_occurrences(user_id,scheduled_date);
CREATE INDEX ix_c3b2b_log_user_occ ON workout_set_logs(user_id,workout_occurrence_id);
CREATE INDEX ix_c3b2b_command_user_occ ON workout_log_commands(user_id,workout_occurrence_id);
CREATE INDEX ix_c3b2b_legacy_log_reference ON workout_set_logs(user_id,workout_id) WHERE workout_occurrence_id IS NULL;
CREATE INDEX ix_c3b2b_legacy_log_receipt ON workout_set_logs(user_id,created_at) WHERE workout_occurrence_id IS NULL;
CREATE INDEX ix_c3b2b_legacy_log_amended ON workout_set_logs(user_id,amended_at) WHERE workout_occurrence_id IS NULL AND amended_at IS NOT NULL;
CREATE INDEX ix_c3b2b_legacy_log_void ON workout_set_logs(user_id,voided_at) WHERE workout_occurrence_id IS NULL AND voided_at IS NOT NULL;
CREATE INDEX ix_c3b2b_legacy_state_receipt ON workout_session_states(user_id,created_at) WHERE workout_occurrence_id IS NULL;
CREATE INDEX ix_c3b2b_legacy_state_updated ON workout_session_states(user_id,updated_at) WHERE workout_occurrence_id IS NULL;

"""
