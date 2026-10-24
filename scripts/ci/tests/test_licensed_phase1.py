import base64
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import os
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "licensed_phase1.py"
spec = importlib.util.spec_from_file_location("licensed_phase1", SCRIPT)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class PrivateFixtureTests(unittest.TestCase):
    def test_exact_bytes_and_private_modes_without_overwrite(self):
        raw = b"synthetic test bytes only" * 5000
        # The real fixed 88,063-byte source is never a test fixture in Git.
        raw = raw[:88063]
        encoded = base64.b64encode(raw).decode()
        parts = [encoded[:40000], encoded[40000:80000], encoded[80000:]]
        with tempfile.TemporaryDirectory() as temp, patch.object(fixture, "DIGEST", hashlib.sha256(raw).hexdigest()):
            root = Path(temp)
            path = fixture.restore(root, parts)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            with self.assertRaises(fixture.FixtureError):
                fixture.restore(root, parts)
            self.assertEqual(path.read_bytes(), raw)

    def test_missing_corrupt_wrong_digest_and_symlinks_fail_closed(self):
        raw = b"x" * 88063
        encoded = base64.b64encode(raw).decode()
        parts = [encoded[:40000], encoded[40000:80000], encoded[80000:]]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for supplied in ([], ["", "", ""], ["private-marker"] * 3,
                             ["!" * 40000, parts[1], parts[2]], parts):
                with self.assertRaises(fixture.FixtureError) as error:
                    fixture.restore(root, supplied)
                self.assertNotIn("private-marker", str(error.exception))
                self.assertFalse((root / fixture.RELATIVE).exists())
            with patch.object(fixture, "DIGEST", hashlib.sha256(raw).hexdigest()):
                (root / "reference").symlink_to(root, target_is_directory=True)
                with self.assertRaises(fixture.FixtureError):
                    fixture.restore(root, parts)
                (root / "reference").unlink()
                (root / "reference").mkdir()
                outside = root / "untouched"
                outside.write_bytes(b"keep")
                (root / fixture.RELATIVE).symlink_to(outside)
                with self.assertRaises(fixture.FixtureError):
                    fixture.restore(root, parts)
                self.assertEqual(outside.read_bytes(), b"keep")

    def test_runner_preserves_selection_exit_status_and_cleans_payload_on_failure(self):
        raw = b"x" * 88063
        encoded = base64.b64encode(raw).decode()
        payload = dict(zip(fixture.SECRET_NAMES, (encoded[:40000], encoded[40000:80000], encoded[80000:])))
        for crash in (False, True):
            with self.subTest(crash=crash), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                script = root / "scripts/ci/licensed_phase1.py"
                script.parent.mkdir(parents=True)
                def run(command, **kwargs):
                    self.assertEqual(command[1:-2], ["-m", "pytest", "-q", "-n", "4", "--dist=loadfile"])
                    self.assertFalse(any(key in os.environ for key in fixture.SECRET_NAMES))
                    self.assertEqual((root / fixture.RELATIVE).read_bytes(), raw)
                    kwargs["stdout"].write(b"private-body-marker")
                    if crash:
                        raise OSError("synthetic unavailable process")
                    Path(command[-1]).write_text('<testsuites><testsuite tests="1" failures="1" errors="0" skipped="0"/></testsuites>')
                    return SimpleNamespace(returncode=1)
                output = io.StringIO()
                with patch.object(fixture, "__file__", str(script)), patch.object(fixture, "DIGEST", hashlib.sha256(raw).hexdigest()), patch.dict(os.environ, payload), patch.object(fixture.subprocess, "run", side_effect=run), redirect_stdout(output):
                    if crash:
                        with self.assertRaises(OSError):
                            fixture.main(["--", "-q", "-n", "4", "--dist=loadfile"])
                    else:
                        self.assertEqual(fixture.main(["--", "-q", "-n", "4", "--dist=loadfile"]), 1)
                self.assertFalse((root / fixture.RELATIVE).exists())
                self.assertNotIn("private-body-marker", output.getvalue())

    def test_failure_report_never_prints_source_assertions_or_captured_output(self):
        xml = ('<testsuites><testsuite tests="4" failures="2" errors="0" skipped="1">'
               '<testcase classname="tests.source" name="test_original"><failure>private-marker</failure>'
               '<system-out>private-marker</system-out></testcase>'
               '<testcase classname="tests.source" name="test_param[private-marker]"><failure>private-marker</failure>'
               '</testcase></testsuite></testsuites>')
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "report.xml"
            report.write_text(xml)
            output = io.StringIO()
            with redirect_stdout(output):
                fixture.summarize(report)
            self.assertIn("1 passed, 2 failed, 0 errors, 1 skipped", output.getvalue())
            self.assertIn("tests.source.test_original", output.getvalue())
            self.assertNotIn("private-marker", output.getvalue())


if __name__ == "__main__":
    unittest.main()
