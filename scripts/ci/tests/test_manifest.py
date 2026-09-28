from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

from test_checks import FakeSnapshot
from check_docs import Snapshot, link_error, structural_errors


CONTEXT = "docs/context/CONTEXT_MANIFEST.yaml"
TARGETS = ("docs/legacy-a.md", "docs/legacy-b.md", "docs/shared.md", "docs/new-a.md", "docs/new-b.md")


def legacy_manifest():
    return {"version": 1, "mandatory_read_groups": [
        {"group": "legacy_policy", "required": True,
         "docs": [{"path": "docs/legacy-a.md"}, {"path": "docs/shared.md"}]},
        {"group": "legacy_workflow", "required": True, "docs": [{"path": "docs/legacy-b.md"}]},
    ]}


def migrated_manifest():
    # Synthetic v2 shape: different groups/paths and no legacy required field.
    return {"version": 2, "mandatory_read_groups": [
        {"group": "new_common", "required_for": ["all changes"], "docs": [{"path": "docs/new-a.md"}]},
        {"group": "new_area", "required_for": ["affected area"], "docs": [{"path": "docs/new-b.md"}]},
    ]}


class ManifestTests(unittest.TestCase):
    def snapshot(self, payload, targets=TARGETS):
        files = {path: "# Synthetic context\n" for path in targets}
        files[CONTEXT] = yaml.safe_dump(payload)
        files["AGENTS.md"] = "# Synthetic agent guidance\n"
        return FakeSnapshot(files)

    def errors(self, payload, base=None, changed=(CONTEXT,), targets=TARGETS):
        snapshot = self.snapshot(payload, targets)
        if base is None:
            return structural_errors(snapshot, set(changed))
        return structural_errors(snapshot, set(changed), base=self.snapshot(base))

    def test_valid_unchanged_manifest_passes(self):
        payload = legacy_manifest()
        self.assertEqual(self.errors(payload, base=deepcopy(payload), changed=()), [])

    def test_mandatory_groups_key_is_required(self):
        self.assertTrue(self.errors({"version": 1}))

    def test_mandatory_groups_must_be_a_nonempty_list(self):
        for groups in ([], None, {}, "legacy_policy"):
            with self.subTest(groups=groups):
                self.assertTrue(self.errors({"version": 1, "mandatory_read_groups": groups}))

    def test_group_docs_must_be_a_nonempty_list(self):
        for docs in ([], None, {}, "docs/legacy-a.md"):
            with self.subTest(docs=docs):
                payload = legacy_manifest()
                payload["mandatory_read_groups"][0]["docs"] = docs
                self.assertTrue(self.errors(payload))

    def test_group_identifiers_must_be_nonempty_strings(self):
        for identifier in (None, "", "  ", 1, []):
            with self.subTest(identifier=identifier):
                payload = legacy_manifest()
                payload["mandatory_read_groups"][0]["group"] = identifier
                self.assertTrue(self.errors(payload))

    def test_duplicate_group_identifiers_fail(self):
        payload = legacy_manifest()
        payload["mandatory_read_groups"].append(deepcopy(payload["mandatory_read_groups"][0]))
        self.assertTrue(self.errors(payload))

    def test_duplicate_paths_within_a_group_fail_across_entry_formats(self):
        payload = legacy_manifest()
        payload["mandatory_read_groups"][0]["docs"].append("docs/legacy-a.md")
        self.assertTrue(self.errors(payload))

    def test_document_paths_must_be_nonempty_strings(self):
        for entry in (None, {}, {"path": ""}, {"path": "  "}, {"path": 1}, []):
            with self.subTest(entry=entry):
                payload = legacy_manifest()
                payload["mandatory_read_groups"][0]["docs"] = [entry]
                self.assertTrue(self.errors(payload))

    def test_missing_referenced_target_fails_even_when_unchanged(self):
        payload = legacy_manifest()
        errors = self.errors(payload, base=deepcopy(payload), changed=(), targets=("docs/legacy-b.md", "docs/shared.md"))
        self.assertTrue(any("does not exist" in error for error in errors), errors)

    def test_same_version_group_removal_fails(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["mandatory_read_groups"].pop()
        self.assertTrue(self.errors(head, base=base))

    def test_same_version_document_removal_fails(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["mandatory_read_groups"][0]["docs"].pop()
        self.assertTrue(self.errors(head, base=base))

    def test_same_version_group_rename_fails_even_if_agents_changes(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["mandatory_read_groups"][0]["group"] = "renamed_policy"
        self.assertTrue(self.errors(head, base=base, changed=(CONTEXT, "AGENTS.md")))

    def test_same_version_document_rename_fails_even_if_new_target_exists(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["mandatory_read_groups"][0]["docs"][0]["path"] = "docs/new-a.md"
        self.assertTrue(self.errors(head, base=base))

    def test_same_version_additive_group_passes_without_agents_change(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["mandatory_read_groups"].append({"group": "extra_context", "docs": ["docs/new-a.md"]})
        self.assertEqual(self.errors(head, base=base), [])

    def test_same_version_additive_document_passes_without_agents_change(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["mandatory_read_groups"][0]["docs"].append("docs/new-a.md")
        self.assertEqual(self.errors(head, base=base), [])

    def test_version_decrease_fails_even_without_mandatory_set_changes(self):
        base = legacy_manifest()
        base["version"] = 2
        self.assertTrue(self.errors(legacy_manifest(), base=base, changed=(CONTEXT, "AGENTS.md")))

    def test_synthetic_v1_to_v2_migration_with_agents_change_passes(self):
        self.assertEqual(self.errors(migrated_manifest(), base=legacy_manifest(), changed=(CONTEXT, "AGENTS.md")), [])

    def test_destructive_version_increase_requires_agents_change(self):
        self.assertTrue(self.errors(migrated_manifest(), base=legacy_manifest()))

    def test_version_increase_cannot_allow_empty_mandatory_groups(self):
        payload = {"version": 2, "mandatory_read_groups": []}
        self.assertTrue(self.errors(payload, base=legacy_manifest(), changed=(CONTEXT, "AGENTS.md")))

    def test_version_increase_cannot_allow_missing_targets(self):
        errors = self.errors(migrated_manifest(), base=legacy_manifest(), changed=(CONTEXT, "AGENTS.md"),
                             targets=("docs/new-a.md",))
        self.assertTrue(any("does not exist" in error for error in errors), errors)

    def test_version_must_be_a_positive_integer(self):
        for version in (None, 0, -1, True, False, "1", 1.0):
            with self.subTest(version=version):
                payload = legacy_manifest()
                payload["version"] = version
                self.assertTrue(self.errors(payload))
        payload = legacy_manifest()
        del payload["version"]
        self.assertTrue(self.errors(payload))

    def test_every_listed_group_is_mandatory_without_legacy_required_metadata(self):
        base = legacy_manifest()
        base["mandatory_read_groups"][0]["required"] = False
        head = deepcopy(base)
        head["mandatory_read_groups"][0]["docs"].pop()
        self.assertTrue(self.errors(head, base=base))

    def test_version_increase_without_removals_does_not_require_agents_change(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["version"] = 2
        self.assertEqual(self.errors(head, base=base), [])

    def test_manifest_and_groups_must_be_mappings(self):
        for payload in (None, [], "manifest", {"version": 1, "mandatory_read_groups": ["group"]}):
            with self.subTest(payload=payload):
                self.assertTrue(self.errors(payload))

    def test_invalid_base_version_cannot_bypass_change_control(self):
        for version in (None, 0, True, "1"):
            with self.subTest(version=version):
                base = legacy_manifest()
                base["version"] = version
                errors = self.errors(migrated_manifest(), base=base, changed=(CONTEXT, "AGENTS.md"))
                self.assertTrue(any("invalid base context manifest" in error for error in errors), errors)

    def test_reordering_and_cross_group_path_reuse_preserve_valid_contracts(self):
        base = legacy_manifest()
        head = deepcopy(base)
        head["mandatory_read_groups"].reverse()
        head["mandatory_read_groups"][1]["docs"].reverse()
        head["mandatory_read_groups"][0]["docs"].append("docs/shared.md")
        self.assertEqual(self.errors(head, base=base), [])

    def test_moving_a_document_between_groups_requires_a_versioned_migration(self):
        base = legacy_manifest()
        head = deepcopy(base)
        document = head["mandatory_read_groups"][0]["docs"].pop()
        head["mandatory_read_groups"][1]["docs"].append(document)
        self.assertTrue(self.errors(head, base=base))

    def test_command_rejects_erosion_but_allows_coordinated_versioned_migration(self):
        for version, agents_changed, expected in ((1, False, 1), (2, False, 1), (2, True, 0)):
            with self.subTest(version=version, agents_changed=agents_changed), \
                    tempfile.TemporaryDirectory(prefix="hypertrophy-ci-context-contract-") as temp:
                root = Path(temp)
                for target in TARGETS:
                    (root / target).parent.mkdir(parents=True, exist_ok=True)
                    (root / target).write_text("# Synthetic target\n")
                (root / CONTEXT).parent.mkdir(parents=True)
                (root / CONTEXT).write_text(yaml.safe_dump(legacy_manifest()))
                (root / "AGENTS.md").write_text("# Legacy context entry point\n")

                def git(*args):
                    return subprocess.check_output([
                        "git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                        "-c", "user.name=CI Fixture", "-c", "user.email=ci-fixture@example.invalid",
                        "-C", temp, *args], stderr=subprocess.DEVNULL).decode().strip()

                git("init", "-q")
                git("add", ".")
                git("commit", "-qm", "synthetic legacy contract")
                base = git("rev-parse", "HEAD")
                payload = migrated_manifest()
                payload["version"] = version
                (root / CONTEXT).write_text(yaml.safe_dump(payload))
                if agents_changed:
                    (root / "AGENTS.md").write_text("# Versioned context entry point\n")
                git("add", ".")
                git("commit", "-qm", "synthetic context edit")
                checker = Path(__file__).resolve().parents[1] / "check_docs.py"
                command = [sys.executable, "-B", str(checker), "--repo", temp, "--base", base]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertIn("New active link failures: 0", result.stdout)
                if expected:
                    self.assertIn(CONTEXT, result.stdout)


class TrackedTargetTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="hypertrophy-ci-tracked-target-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "docs/architecture").mkdir(parents=True)
        (self.root / CONTEXT).parent.mkdir(parents=True)
        (self.root / "README.md").write_text("# Synthetic index\n")
        for target in ("system.md", "policy.yaml", "source.txt"):
            (self.root / "docs/architecture" / target).write_text("# Synthetic document\n")
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.check_output([
            "git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
            "-c", "user.name=CI Fixture", "-c", "user.email=ci-fixture@example.invalid",
            "-C", str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def snapshot(self, target):
        payload = {"version": 1, "mandatory_read_groups": [{"group": "context", "docs": [{"path": target}]}]}
        (self.root / CONTEXT).write_text(yaml.safe_dump(payload))
        self.git("add", ".")
        self.git("commit", "-qm", "synthetic tracked target")
        return Snapshot(self.root, "HEAD")

    def test_exact_tracked_manifest_files_pass(self):
        for target in ("docs/architecture/system.md", "docs/architecture/policy.yaml", "docs/architecture/source.txt"):
            with self.subTest(target=target):
                snapshot = self.snapshot(target)
                self.assertIn(target, snapshot.paths)
                self.assertEqual(structural_errors(snapshot, {CONTEXT}), [])

    def test_missing_manifest_file_fails(self):
        snapshot = self.snapshot("docs/missing.md")
        errors = structural_errors(snapshot, {CONTEXT})
        self.assertTrue(any("does not exist" in error and "docs/missing.md" in error for error in errors), errors)

    def test_manifest_directory_with_tracked_children_fails(self):
        snapshot = self.snapshot("docs/architecture")
        self.assertTrue(snapshot.exists("docs/architecture"))
        self.assertNotIn("docs/architecture", snapshot.paths)
        errors = structural_errors(snapshot, {CONTEXT})
        self.assertTrue(any("docs/architecture" in error for error in errors), errors)

    def test_ordinary_markdown_directory_links_still_pass(self):
        snapshot = self.snapshot("docs/architecture/system.md")
        for target in ("docs/architecture", "docs/architecture/"):
            with self.subTest(target=target):
                self.assertTrue(snapshot.exists(target))
                self.assertIsNone(link_error(snapshot, "README.md", target))


if __name__ == "__main__":
    unittest.main()
