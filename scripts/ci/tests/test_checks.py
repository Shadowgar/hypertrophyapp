import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from changes import changed_paths, classify, sha
from check_docs import active_text, anchors, links, link_error, release_schema_errors, structural_errors
from gate import JOBS, evaluate


class SelectionTests(unittest.TestCase):
    def test_documentation_does_not_run_application_tests(self):
        selected = classify(["README.md", "AGENTS.md", "SECURITY.md", "docs/quality/example.schema.json",
                             "docs/guides/FULL_EXTRACTION_RUNBOOK.md", "docs/guides/generated/README.md"])
        self.assertTrue(selected["docs"])
        self.assertFalse(any(selected[key] for key in ("api", "core", "web")))
        self.assertFalse(selected["containers"])

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
        self.assertTrue(selected["containers"])

    def test_real_container_definitions_select_builds_and_preserve_runtime_coverage(self):
        expected = {
            "apps/api/Dockerfile": {"api"},
            "apps/web/Dockerfile": {"web"},
            "docker-compose.yml": {"api", "core", "web"},
            ".dockerignore": {"api", "core", "web"},
        }
        for path, runtime in expected.items():
            with self.subTest(path=path):
                selected = classify([path])
                self.assertTrue(selected["containers"])
                self.assertEqual({key for key in ("api", "core", "web") if selected[key]}, runtime)

    def test_api_python_changes_do_not_build_containers_unless_another_input_requires_it(self):
        path = "apps/api/app/config.py"
        selected = classify([path])
        self.assertTrue(selected["api"])
        self.assertFalse(selected["containers"])
        self.assertTrue(classify([path, "apps/api/Dockerfile"])["containers"])

    def test_workflow_changes_run_tooling_checks(self):
        self.assertTrue(classify([".github/workflows/ci.yml"])["tooling"])
        self.assertTrue(classify(["scripts/ci/check_docs.py"])["tooling"])

    def test_event_sha_cannot_be_an_option_or_ref_expression(self):
        for value in ("--help", "main", "a" * 39, "a" * 40 + "\n", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sha(value)
        self.assertEqual(sha("a" * 40), "a" * 40)

    def test_push_keeps_before_commit_for_both_baselines(self):
        event = {"before": "a" * 40, "after": "b" * 40}
        with patch("changes.git", return_value=b"README.md\0") as git:
            self.assertEqual(changed_paths("push", event), (event["before"], event["before"], ["README.md"]))
        git.assert_called_once_with("diff", "--name-only", "--no-renames", "-z", event["before"], event["after"])

    def test_dispatch_and_initial_push_keep_full_coverage_without_a_baseline(self):
        self.assertEqual(changed_paths("workflow_dispatch", {}), (None, None, None))
        self.assertEqual(changed_paths("push", {"before": "0" * 40, "after": "b" * 40}),
                         (None, None, None))


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

    def test_required_container_build_failures_cancellations_and_skips_fail_qualification(self):
        for state in ("success", "failure", "cancelled", "skipped"):
            with self.subTest(state=state):
                needs = self.needs()
                needs["changes"]["outputs"]["containers"] = "true"
                needs["container-build"] = {"result": state}
                errors = evaluate(needs)
                if state == "success":
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(any("container-build" in error for error in errors), errors)

    def test_missing_or_invalid_container_applicability_fails_qualification(self):
        for flag in (None, "", "invalid"):
            with self.subTest(flag=flag):
                needs = self.needs()
                if flag is None:
                    needs["changes"]["outputs"].pop("containers", None)
                else:
                    needs["changes"]["outputs"]["containers"] = flag
                self.assertTrue(any("containers" in error for error in evaluate(needs)))


class ConfigDefaultTests(unittest.TestCase):
    def run_default_check(self, true_default=False):
        repo = Path(__file__).resolve().parents[3]
        workflow = yaml.safe_load((repo / ".github/workflows/ci.yml").read_text())
        step = next(step for step in workflow["jobs"]["api-tests"]["steps"]
                    if step.get("name") == "Verify settings defaults with dev flag absent")
        source = (repo / "apps/api/app/config.py").read_text()
        if true_default:
            tree = ast.parse(source)
            settings = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Settings")
            default = next(node for node in settings.body if isinstance(node, ast.AnnAssign)
                           and isinstance(node.target, ast.Name) and node.target.id == "allow_dev_wipe_endpoints")
            default.value = ast.Constant(True)
            source = ast.unparse(tree)
        with tempfile.TemporaryDirectory(prefix="hypertrophy-ci-default-test-") as temp:
            root = Path(temp)
            (root / "app").mkdir()
            (root / "app/__init__.py").write_text("")
            (root / "app/config.py").write_text(source)
            # A dotenv override must not replace the default under test.
            (root / ".env").write_text("ALLOW_DEV_WIPE_ENDPOINTS=true\n")
            poison = ("import os\nfrom pathlib import Path\n"
                      "Path('pytest-setup-imported').write_text('loaded')\n"
                      "os.environ.setdefault('ALLOW_DEV_WIPE_ENDPOINTS', 'true')\n"
                      "raise RuntimeError('pytest setup must not run before the assertion')\n")
            (root / "pytest.py").write_text(poison)
            (root / "conftest.py").write_text(poison)
            (root / "tests").mkdir()
            (root / "tests/conftest.py").write_text(poison)
            env = {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
                   "PYTHONDONTWRITEBYTECODE": "1", "ALLOW_DEV_WIPE_ENDPOINTS": "true"}
            result = subprocess.run(["bash", "-euo", "pipefail", "-c", step["run"]],
                                    cwd=temp, env=env, capture_output=True, text=True)
            self.assertFalse((root / "pytest-setup-imported").exists(), result.stdout + result.stderr)
            return result

    def test_current_false_default_passes_outside_pytest_with_the_flag_removed(self):
        result = self.run_default_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_true_runtime_default_fails_the_same_isolated_check(self):
        result = self.run_default_check(true_default=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dev wipe endpoints must default to false", result.stderr)


class ContainerCommandTests(unittest.TestCase):
    def test_workflow_build_command_propagates_compose_and_build_failures_to_the_gate(self):
        repo = Path(__file__).resolve().parents[3]
        workflow = yaml.safe_load((repo / ".github/workflows/ci.yml").read_text())
        job = workflow["jobs"]["container-build"]
        self.assertEqual(job["if"], "needs.changes.outputs.containers == 'true'")
        self.assertIn("container-build", workflow["jobs"]["qualification"]["needs"])
        command = next(step["run"] for step in job["steps"] if "run" in step)
        expected = [
            ["compose", "--env-file", "/dev/null", "-f", "docker-compose.yml", "config", "--quiet"],
            ["compose", "--env-file", "/dev/null", "-f", "docker-compose.yml", "build", "--pull"],
        ]
        for failure in ("", "config", "build"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(prefix="hypertrophy-ci-build-test-") as temp:
                root = Path(temp)
                docker = root / "docker"
                docker.write_text(f"#!{sys.executable}\n"
                                  "import json, os, sys\n"
                                  "with open(os.environ['CI_TEST_DOCKER_CALLS'], 'a') as calls:\n"
                                  "    calls.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                                  "raise SystemExit(17 if os.environ['CI_TEST_DOCKER_FAILURE'] in ('config', 'build') "
                                  "and os.environ['CI_TEST_DOCKER_FAILURE'] in sys.argv[1:] else 0)\n")
                docker.chmod(0o700)
                calls = root / "calls.jsonl"
                env = {"PATH": str(root) + os.pathsep + os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
                       "CI_TEST_DOCKER_CALLS": str(calls), "CI_TEST_DOCKER_FAILURE": failure}
                result = subprocess.run(["bash", "-euo", "pipefail", "-c", command],
                                        cwd=temp, env=env, capture_output=True, text=True)
                recorded = [json.loads(line) for line in calls.read_text().splitlines()]
                self.assertEqual(recorded, expected[:1] if failure == "config" else expected)
                self.assertEqual(result.returncode == 0, not failure, result.stdout + result.stderr)
                needs = {"changes": {"result": "success", "outputs": {key: "false" for key in JOBS}}}
                needs["changes"]["outputs"]["containers"] = "true"
                for category, jobs in JOBS.items():
                    for name in jobs:
                        needs[name] = {"result": ("failure" if failure else "success")
                                       if category == "containers" else "skipped"}
                self.assertEqual(bool(evaluate(needs)), bool(failure))


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
                                 "version: 1\nmandatory_read_groups:\n- group: context\n  docs:\n  - path: docs/deleted.md\n"})
        self.assertTrue(any("does not exist" in error for error in structural_errors(snapshot, set())))

    def test_valid_context_manifest_passes_even_if_unchanged(self):
        snapshot = FakeSnapshot({"docs/context/CONTEXT_MANIFEST.yaml":
                                 "version: 1\nmandatory_read_groups:\n- group: context\n  docs:\n  - path: docs/required.md\n",
                                 "docs/required.md": "# Required context\n"})
        self.assertEqual(structural_errors(snapshot, set()), [])

    def test_missing_canonical_context_manifest_fails_even_after_rename(self):
        for files in ({}, {"docs/context/RENAMED_MANIFEST.yaml": "mandatory_read_groups: []\n"}):
            with self.subTest(files=files):
                errors = structural_errors(FakeSnapshot(files), set())
                self.assertTrue(any("docs/context/CONTEXT_MANIFEST.yaml" in error and "mandatory" in error
                                    for error in errors), errors)


class CommandTests(unittest.TestCase):
    manifest = "version: 1\nmandatory_read_groups:\n- group: context\n  docs:\n  - path: README.md\n"

    def test_baseline_links_are_visible_and_new_errors_return_nonzero(self):
        with tempfile.TemporaryDirectory(prefix="hypertrophy-ci-check-test-") as temp:
            root = Path(temp)
            (root / "README.md").write_text("# Index\n\n[old failure](old-missing.md)\n")
            (root / "docs/context").mkdir(parents=True)
            (root / "docs/context/CONTEXT_MANIFEST.yaml").write_text(self.manifest)
            def git(*args):
                return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                                                "-c", "user.name=CI Fixture", "-c", "user.email=ci-fixture@example.invalid",
                                                "-C", temp, *args], stderr=subprocess.DEVNULL).decode().strip()
            git("init", "-q")
            git("add", "README.md", "docs/context/CONTEXT_MANIFEST.yaml")
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

    def test_pr_merge_snapshot_uses_current_base_after_branch_divergence(self):
        with tempfile.TemporaryDirectory(prefix="hypertrophy-ci-pr-base-test-") as temp:
            root = Path(temp)
            (root / "docs/context").mkdir(parents=True)
            (root / "docs/context/CONTEXT_MANIFEST.yaml").write_text(self.manifest)
            (root / "README.md").write_text("# Index\n")

            def git(*args):
                return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                                                "-c", "user.name=CI Fixture", "-c", "user.email=ci-fixture@example.invalid",
                                                "-C", temp, *args], stderr=subprocess.DEVNULL).decode().strip()

            git("init", "-q", "-b", "main")
            git("add", ".")
            git("commit", "-qm", "synthetic divergence point")
            divergence = git("rev-parse", "HEAD")
            git("checkout", "-qb", "docs-review")
            (root / "docs/pr.md").write_text("# PR documentation\n")
            git("add", ".")
            git("commit", "-qm", "synthetic PR documentation")
            pr_head = git("rev-parse", "HEAD")
            git("checkout", "-q", "main")
            (root / "docs/base-only.md").write_text("# Base documentation\n\n[base-only failure](base-missing.md)\n")
            git("add", ".")
            git("commit", "-qm", "synthetic later base documentation")
            current_base = git("rev-parse", "HEAD")
            git("merge", "--no-ff", "-qm", "synthetic PR merge checkout", "docs-review")
            self.assertNotEqual(current_base, divergence)

            helpers = Path(__file__).resolve().parents[1]
            event_path = root / "event.json"
            event_path.write_text(json.dumps({"pull_request": {"base": {"sha": current_base},
                                                              "head": {"sha": pr_head}}}))
            output_path = root / "github-output.txt"
            env = {key: value for key, value in os.environ.items()
                   if key not in ("GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY")}
            env.update(GITHUB_EVENT_NAME="pull_request", GITHUB_EVENT_PATH=str(event_path),
                       GITHUB_OUTPUT=str(output_path))
            for arguments in ([], ["--base", current_base, "--head", pr_head]):
                with self.subTest(arguments=arguments):
                    output_path.write_text("")
                    result = subprocess.run([sys.executable, "-B", str(helpers / "changes.py"), *arguments],
                                            cwd=temp, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    report = json.loads(result.stdout)
                    outputs = dict(line.split("=", 1) for line in output_path.read_text().splitlines())
                    # Use the same output consumed by the workflow's documentation job.
                    result = subprocess.run([sys.executable, "-B", str(helpers / "check_docs.py"),
                                             "--repo", temp, "--base", outputs["base"]],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("Existing active link failures retained: 1", result.stdout)
                    self.assertIn("New active link failures: 0", result.stdout)
                    self.assertEqual(report["base"], current_base)
                    self.assertEqual(report["diff_base"], divergence)
                    self.assertEqual(outputs["diff_base"], divergence)
                    self.assertEqual(report["changed_files"], 1)
                    self.assertTrue(report["docs"] and report["tooling"])
                    self.assertFalse(any(report[category] for category in ("api", "core", "web")))

    def test_manifest_deletion_and_rename_fail_without_markdown_links(self):
        for rename in (False, True):
            with self.subTest(rename=rename), tempfile.TemporaryDirectory(prefix="hypertrophy-ci-manifest-test-") as temp:
                root = Path(temp)
                context = "docs/context/CONTEXT_MANIFEST.yaml"
                (root / "docs/context").mkdir(parents=True)
                (root / context).write_text(self.manifest)
                (root / "README.md").write_text("# Index\n")

                def git(*args):
                    return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                                                    "-c", "user.name=CI Fixture", "-c", "user.email=ci-fixture@example.invalid",
                                                    "-C", temp, *args], stderr=subprocess.DEVNULL).decode().strip()

                git("init", "-q")
                git("add", ".")
                git("commit", "-qm", "synthetic valid manifest")
                base = git("rev-parse", "HEAD")
                checker = Path(__file__).resolve().parents[1] / "check_docs.py"
                command = [sys.executable, "-B", str(checker), "--repo", temp, "--base", base]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if rename:
                    git("mv", context, "docs/context/RENAMED_MANIFEST.yaml")
                else:
                    git("rm", "--", context)
                git("commit", "-qm", "synthetic removed canonical manifest")
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("New active link failures: 0", result.stdout)
                self.assertIn(context + ": mandatory context manifest is missing", result.stdout)


if __name__ == "__main__":
    unittest.main()
