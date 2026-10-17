-- Disposable-only source query qualification. NOT a production migration.
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
