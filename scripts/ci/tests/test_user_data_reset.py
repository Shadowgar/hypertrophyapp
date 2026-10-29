"""Reset operator boundary tests: no implicit target or destructive defaults."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def tool():
    path = ROOT / "scripts/reset_user_data.py"
    assert path.exists(), "Guarded reset tool is missing"
    spec = importlib.util.spec_from_file_location("guarded_reset", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def catalog():
    names = ["alembic_version", "authored_initial_calibrations", "authored_load_states", "body_measurement_entries", "coaching_recommendations", "customized_candidate_commands", "customized_candidate_events", "customized_candidate_heads", "customized_candidate_schema", "customized_candidate_sessions", "customized_equipment_profiles", "exercise_states", "password_reset_tokens", "soreness_entries", "user_interface_preferences", "users", "weekly_checkins", "weekly_review_cycles", "workout_log_commands", "workout_occurrences", "workout_plans", "workout_session_states", "workout_set_logs"]
    tables = [{"schema": "public", "name": n, "kind": "r"} for n in names]
    fks = [{"child_schema":"public","child":n,"parent_schema":"public","parent":"users"} for n in names if n not in {"alembic_version","customized_candidate_schema","users","customized_candidate_heads"}]
    fks += [{"child_schema":"public","child":"customized_candidate_heads","parent_schema":"public","parent":"customized_candidate_events"}, {"child_schema":"public","child":"workout_set_logs","parent_schema":"public","parent":"workout_occurrences"}, {"child_schema":"public","child":"workout_set_logs","parent_schema":"public","parent":"workout_set_logs"}]
    return {"tables":tables,"foreign_keys":fks,"triggers":[],"rules":[]}


class TestOperatorGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_unknown_or_indirect_mutation_scope_is_rejected(self):
        for change in ["unknown_table","external_fk","trigger","rule","missing_table","preserved_child","orphan_owner"]:
            with self.subTest(change=change):
                self.check_unknown_or_indirect_mutation_scope_is_rejected(change)

    def test_legacy_entrypoint_without_explicit_target_never_calls_docker(self):
        tmp_path = Path(self.tmp.name)
        marker = tmp_path / "docker-called"
        fake = tmp_path / "docker"
        fake.write_text("#!/bin/sh\ntouch '" + str(marker) + "'\nexit 0\n")
        fake.chmod(0o700)
        env = dict(os.environ, PATH=str(tmp_path) + ":" + os.environ["PATH"])
        result = subprocess.run(["bash", str(ROOT / "scripts/reset_testing_user_data.sh")], env=env, capture_output=True, text=True)
        assert result.returncode != 0, "Unqualified invocation must refuse"
        assert not marker.exists(), "No target was approved: do not contact Docker"


    def test_reset_scope_preserves_both_schema_state_tables_and_orders_dependents(self):
        order = tool().validate_catalog(catalog())
        assert len(order) == 21
        assert "alembic_version" not in order
        assert "customized_candidate_schema" not in order
        assert order.index("customized_candidate_heads") < order.index("customized_candidate_events")
        assert order.index("workout_set_logs") < order.index("workout_occurrences")
        assert order[-1] == "users"


    def check_unknown_or_indirect_mutation_scope_is_rejected(self, change):
        m=tool(); c=catalog()
        if change=="unknown_table": c["tables"].append({"schema":"public","name":"future_history","kind":"r"})
        if change=="external_fk": c["foreign_keys"].append({"child_schema":"other","child":"ledger","parent_schema":"public","parent":"users"})
        if change=="trigger": c["triggers"].append({"name":"unexpected_delete_trigger"})
        if change=="rule": c["rules"].append({"name":"unexpected_delete_rule"})
        if change=="missing_table": c["tables"].pop()
        if change=="preserved_child": c["foreign_keys"].append({"child_schema":"public","child":"customized_candidate_schema","parent_schema":"public","parent":"users"})
        if change=="orphan_owner": c["foreign_keys"]=[f for f in c["foreign_keys"] if f["child"]!="customized_candidate_heads"]
        with self.assertRaises(m.ResetRefused): m.validate_catalog(c)


    def test_private_artifact_writes_do_not_overwrite_or_follow_symlinks(self):
        tmp_path = Path(self.tmp.name)
        m=tool(); p=tmp_path/"receipt.json"
        m.write_private(p,{"ok":True})
        assert p.stat().st_mode & 0o777 == 0o600
        with self.assertRaises(m.ResetRefused):m.write_private(p,{"changed":True})
        link=tmp_path/"link";link.symlink_to(p)
        with self.assertRaises(m.ResetRefused):m.write_private(link,{"changed":True})


    def test_application_reset_requires_exact_manifest_and_restore_evidence(self):
        m=tool()
        with self.assertRaises(m.ResetRefused):m.require_approval({"kind":"production","app_revision":"a"*40},"a"*64,"b"*64,None,None)
        with self.assertRaises(m.ResetRefused):m.require_approval({"kind":"production","app_revision":"a"*40},"a"*64,"a"*64,None,None)


    def test_inherited_environment_never_supplies_cli_target(self):
        m=tool()
        env=dict(os.environ, POSTGRES_DB="hypertrophy", POSTGRES_USER="hypertrophy", DATABASE_URL="postgresql://production.invalid/live")
        r=subprocess.run([sys.executable,str(ROOT/"scripts/reset_user_data.py"),"prepare"],env=env,capture_output=True,text=True)
        assert r.returncode!=0
        assert "required" in r.stderr.lower()


    def test_restore_check_accepts_only_measured_check_cast_normalization(self):
        m=tool(); import copy
        source={"catalog":catalog(),"tables":[{"table":"users","count":9,"sha256":"a"*64}],"delete_order":["users"],"schema_sha256":"a"*64}
        source["catalog"]["constraints"]=[["public","user_interface_preferences","ck_ui_preference_unit", "CHECK (((weight_unit)::text = ANY ((ARRAY['kg'::character varying, 'lb'::character varying])::text[])))"]]
        restored=copy.deepcopy(source);restored["schema_sha256"]="b"*64
        restored["catalog"]["constraints"][0][3]="CHECK (((weight_unit)::text = ANY (ARRAY[('kg'::character varying)::text, ('lb'::character varying)::text])))"
        assert m.restoration_matches(source,restored)
        restored["catalog"]["constraints"][0][3]="CHECK (true)"
        assert not m.restoration_matches(source,restored)
        restored=copy.deepcopy(source);restored["tables"][0]["count"]=0
        assert not m.restoration_matches(source,restored)
