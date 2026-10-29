"""Opt-in destructive rehearsal ONLY in a previously verified disposable restore.

Normal CI skips this operator rehearsal; pure guard tests run in every tooling
job. Set both explicit artifact paths after verify-restore to run the real PG test.
"""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get("RESET_REHEARSAL_MANIFEST") and os.environ.get("RESET_REHEARSAL_RECEIPT"),
                     "Requires explicit private manifest and disposable restore receipt")
class TestPostgresResetRehearsal(unittest.TestCase):
    def test_atomic_failure_stale_inventory_and_complete_reset(self):
        root = Path(__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location("reset_operator_pg", root / "scripts/reset_user_data.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        manifest_path = Path(os.environ["RESET_REHEARSAL_MANIFEST"])
        receipt_path = Path(os.environ["RESET_REHEARSAL_RECEIPT"])
        receipt = m.read_private(receipt_path)
        target = receipt["target"]
        self.assertEqual(target["kind"], "disposable")
        m.verify_target(target)  # immutable ID, tmpfs, label, database/user/cluster
        before = m.capture(target)
        self.assertGreater(next(x["count"] for x in before["tables"] if x["table"] == "users"), 0,
                           "Requires a fresh restored fixture, not a previously reset DB")
        digest = m.file_hash(manifest_path)
        out = Path(tempfile.mkdtemp(prefix="reset-rehearsal-", dir=manifest_path.parent))

        def execute(audit, *, really=True):
            return m.apply_reset(manifest_path, digest, receipt_path, None, out / audit,
                                 execute=really, rehearsal_container=target["container"])

        self.assertEqual(execute("unused.json", really=False)["status"], "dry_run_only")
        self.assertEqual(m.capture(target), before)
        self.assertFalse((out / "unused.json").exists())

        # A schema-state change between approval and execution must stop all deletes.
        m.sql(target, "BEGIN; UPDATE public.alembic_version SET version_num='unexpected_rehearsal_revision'; COMMIT;", readonly=False)
        with self.assertRaises(m.ResetRefused):
            execute("stale-denied.json")
        self.assertFalse((out / "stale-denied.json").exists())
        m.sql(target, "BEGIN; UPDATE public.alembic_version SET version_num='0026_initial_calibration'; COMMIT;", readonly=False)
        self.assertEqual(m.capture(target), before)

        # Force a real PostgreSQL error after deleting populated rows. An error
        # after an empty-table DELETE would not establish data rollback.
        original = m.deletion_sql(target, before)
        counts = {t["table"]: t["count"] for t in before["tables"]}
        populated = next(n for n in before["delete_order"] if counts[n] > 0)
        self.assertGreater(counts[populated], 0)
        deletion = 'DELETE FROM public."' + populated + '";'
        injected = ("\nDO $$ BEGIN IF EXISTS (SELECT 1 FROM public.\"" + populated +
                    "\") THEN RAISE EXCEPTION 'delete did not occur'; END IF; "
                    "RAISE EXCEPTION 'injected rehearsal failure'; END $$;")
        broken = original.replace(deletion, deletion + injected, 1)
        self.assertNotEqual(broken, original)
        with patch.object(m, "deletion_sql", return_value=broken):
            with self.assertRaises(m.ResetRefused):
                execute("rollback.private.json")
        self.assertEqual(m.capture(target), before)
        self.assertEqual(m.read_private(out / "rollback.private.json")["status"], "not_confirmed_inspect_before_retry")
        print("Rollback verified after deleting populated table:", populated, "rows:", counts[populated])

        result = execute("success.private.json")
        self.assertEqual(result["status"], "reset_verified")
        after = m.capture(target)
        self.assertEqual(after["schema_sha256"], before["schema_sha256"])
        self.assertTrue(all(t["count"] == 0 for t in after["tables"] if t["table"] in m.DELETE))
        self.assertEqual([t for t in after["tables"] if t["table"] in m.PRESERVE],
                         [t for t in before["tables"] if t["table"] in m.PRESERVE])
        print("Disposable reset verified; private audit directory:", out)


if __name__ == "__main__":
    unittest.main()
