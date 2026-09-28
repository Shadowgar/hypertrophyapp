from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from changes import classify, sha
from check_docs import active_text, anchors, links, link_error, release_schema_errors, structural_errors
from gate import JOBS, evaluate


class SelectionTests(unittest.TestCase):
    def test_documentation_does_not_run_application_tests(self):
        selected = classify(["README.md", "AGENTS.md", "SECURITY.md", "docs/quality/example.schema.json",
                             "docs/guides/FULL_EXTRACTION_RUNBOOK.md", "docs/guides/generated/README.md"])
        self.assertTrue(selected["docs"])
        self.assertFalse(any(selected[key] for key in ("api", "core", "web")))

    def test_runtime_docs_and_training_artifacts_are_not_prose(self):
        for path in ("docs/rules/policy.json", "programs/gold/plan.json", "knowledge/compiled/guide.md",
                     "importers/compiler.py", "docs/guides/asset_catalog.json", "docs/guides/generated/guide.md"):
            with self.subTest(path=path):
                selected = classify([path])
                self.assertTrue(selected["api"] and selected["core"])

    def test_component_and_shared_dependency_coverage(self):
        self.assertTrue(classify(["apps/api/app/routers/auth.py"])["api"])
        selected = classify(["packages/core-engine/core_engine/intelligence.py"])
        self.assertTrue(selected["api"] and selected["core"])
        self.assertFalse(selected["web"])
        selected = classify(["apps/web/components/example.tsx"])
        self.assertTrue(selected["web"])
        self.assertFalse(selected["api"] or selected["core"])

    def test_unknown_inputs_conservatively_run_runtime_checks(self):
        selected = classify(["new-shared-build-config.toml"])
        self.assertTrue(all(selected[key] for key in ("api", "core", "web")))

    def test_workflow_changes_run_tooling_checks(self):
        self.assertTrue(classify([".github/workflows/ci.yml"])["tooling"])
        self.assertTrue(classify(["scripts/ci/check_docs.py"])["tooling"])

    def test_event_sha_cannot_be_an_option_or_ref_expression(self):
        for value in ("--help", "main", "a" * 39, "a" * 40 + "\n", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sha(value)
        self.assertEqual(sha("a" * 40), "a" * 40)


class GateTests(unittest.TestCase):
    def needs(self):
        result = {"changes": {"result": "success", "outputs": {key: "false" for key in JOBS}}}
        result["changes"]["outputs"]["docs"] = "true"
        for category, jobs in JOBS.items():
            for job in jobs:
                result[job] = {"result": "success" if category == "docs" else "skipped"}
        return result

    def test_documentation_pass_with_inapplicable_runtime_jobs(self):
        self.assertEqual(evaluate(self.needs()), [])

    def test_required_job_failure_cancellation_and_skip_are_not_passes(self):
        for state in ("failure", "cancelled", "skipped"):
            needs = self.needs()
            needs["documentation"]["result"] = state
            self.assertTrue(evaluate(needs))

    def test_classifier_failure_cannot_be_hidden_by_skipped_jobs(self):
        needs = self.needs()
        needs["changes"]["result"] = "failure"
        needs["changes"]["outputs"] = {}
        self.assertTrue(evaluate(needs))

    def test_missing_applicability_output_cannot_be_treated_as_not_applicable(self):
        needs = self.needs()
        del needs["changes"]["outputs"]["api"]
        self.assertTrue(evaluate(needs))


class FakeSnapshot:
    def __init__(self, files):
        self.files = files
        self.paths = set(files)

    def text(self, path):
        return self.files[path]

    def exists(self, path):
        return path in self.paths or any(p.startswith(path.rstrip("/") + "/") for p in self.paths)


class LinkTests(unittest.TestCase):
    def test_reference_links_images_and_fenced_examples(self):
        text = '[Guide][g]\n\n[g]: other.md#heading\n\n![diagram](diagram.svg)\n\n```md\n[example](missing.md)\n```\n'
        self.assertEqual(list(links(text)), ["other.md#heading", "diagram.svg"])

    def test_duplicate_headings_and_explicit_anchors(self):
        text = '# First **heading**\n\n## First heading\n\n<a id="custom"></a>\n'
        self.assertTrue({"first-heading", "first-heading-1", "custom"} <= anchors(text))

    def test_missing_and_invalid_source_anchors_fail(self):
        snapshot = FakeSnapshot({"docs/guide.md": "# Heading\n", "scripts/example.py": "first\nsecond\n"})
        self.assertIsNone(link_error(snapshot, "docs/guide.md", "#heading"))
        self.assertEqual(link_error(snapshot, "docs/guide.md", "#absent"), "missing Markdown anchor")
        self.assertEqual(link_error(snapshot, "docs/guide.md", "../scripts/example.py#L3"), "invalid source-line anchor")
        self.assertEqual(link_error(snapshot, "docs/guide.md", "missing.md"), "missing path")

    def test_portable_paths_and_external_links(self):
        snapshot = FakeSnapshot({"docs/my guide.md": "# Heading\n"})
        self.assertIsNone(link_error(snapshot, "docs/index.md", "my%20guide.md#heading"))
        self.assertIsNone(link_error(snapshot, "docs/index.md", "https://example.invalid/not-probed"))
        self.assertEqual(link_error(snapshot, "docs/index.md", "/home/example/file.md"), "absolute local/host path")
        self.assertEqual(link_error(snapshot, "docs/index.md", "../../private.md"), "path outside repository")

    def test_historical_successor_notice_is_checked_without_requalifying_body(self):
        notice = '> **Historical / archived.** Current successor: [index](../README.md).\n\n'
        original = '# Old findings\n\n[dated missing artifact](missing.md)\n'
        self.assertEqual(active_text(notice + original), notice)
        self.assertEqual(list(links(active_text(notice + original))), ["../README.md"])
        self.assertEqual(active_text(original), original)


class SchemaTests(unittest.TestCase):
    def schema(self):
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
            "properties": {"owner_acceptance": {"enum": ["pending", "accepted", "rejected"]},
                           "evidence": {"type": "array"}},
            "allOf": [{"if": {"properties": {"owner_acceptance": {"const": "accepted"}}},
                       "then": {"properties": {"evidence": {"minItems": 1}},
                                "required": ["evidence", "acceptance_reference"]}}],
        }

    def test_pending_records_can_be_empty_and_accepted_records_need_evidence(self):
        self.assertEqual(release_schema_errors(self.schema()), [])

    def test_missing_accepted_state_minimum_is_reported(self):
        schema = self.schema()
        del schema["allOf"][0]["then"]["properties"]
        self.assertTrue(release_schema_errors(schema))

    def test_rejecting_every_acceptance_is_not_a_valid_fix(self):
        schema = self.schema()
        schema["properties"]["owner_acceptance"]["enum"] = ["pending", "rejected"]
        self.assertTrue(any("evidenced" in error for error in release_schema_errors(schema)))

    def test_remote_schema_references_fail_without_network_resolution(self):
        schema = self.schema()
        schema["$ref"] = "https://example.invalid/unavailable-schema"
        with self.assertRaises(Exception) as caught:
            release_schema_errors(schema)
        self.assertIn("Unresolvable", str(caught.exception))

    def test_deleting_a_context_target_fails_even_if_manifest_is_unchanged(self):
        snapshot = FakeSnapshot({"docs/context/CONTEXT_MANIFEST.yaml":
                                 "mandatory_read_groups:\n- group: context\n  docs:\n  - path: docs/deleted.md\n"})
        self.assertTrue(any("does not exist" in error for error in structural_errors(snapshot, set())))


class CommandTests(unittest.TestCase):
    def test_baseline_links_are_visible_and_new_errors_return_nonzero(self):
        with tempfile.TemporaryDirectory(prefix="hypertrophy-ci-check-test-") as temp:
            root = Path(temp)
            (root / "README.md").write_text("# Index\n\n[old failure](old-missing.md)\n")
            def git(*args):
                return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                                                "-c", "user.name=CI Fixture", "-c", "user.email=ci-fixture@example.invalid",
                                                "-C", temp, *args], stderr=subprocess.DEVNULL).decode().strip()
            git("init", "-q")
            git("add", "README.md")
            git("commit", "-qm", "synthetic baseline")
            base = git("rev-parse", "HEAD")
            checker = Path(__file__).resolve().parents[1] / "check_docs.py"
            command = [sys.executable, "-B", str(checker), "--repo", temp, "--base", base, "--worktree"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Existing active link failures retained: 1", result.stdout)
            (root / "README.md").write_text("# Index\n\n[old failure](old-missing.md)\n[new failure](new-missing.md)\n")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("New active link failures: 1", result.stdout)


if __name__ == "__main__":
    unittest.main()
