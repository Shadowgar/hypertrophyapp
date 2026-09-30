"""Select CI categories using the complete Git diff, without a files API limit."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess


CATEGORIES = ("docs", "api", "core", "web", "tooling", "containers")
CONTAINER_DEFINITIONS = {"apps/api/Dockerfile", "apps/web/Dockerfile", "docker-compose.yml", ".dockerignore"}


def classify(paths):
    selected = {key: False for key in CATEGORIES}
    for path in paths:
        if path in CONTAINER_DEFINITIONS:
            selected["containers"] = True
        if path == ".github/workflows/ci.yml":
            # Exercise the job graph when changing the workflow itself.
            selected["tooling"] = selected["api"] = selected["core"] = selected["web"] = True
        elif path.startswith(".github/") or path.startswith("scripts/ci/"):
            selected["tooling"] = True
        elif path.startswith(("docs/rules/", "programs/", "knowledge/", "importers/", "reference/")):
            selected["api"] = selected["core"] = True
        elif (path.startswith("docs/guides/generated/") and not path.endswith("/README.md")) or (
            path.startswith("docs/guides/") and path.endswith(".json")
        ):
            selected["api"] = selected["core"] = True
        elif path.endswith(".md") or path.startswith("docs/"):
            selected["docs"] = True
        elif path.startswith("apps/api/"):
            selected["api"] = True
        elif path.startswith("packages/core-engine/"):
            selected["api"] = selected["core"] = True
        elif path.startswith("apps/web/"):
            selected["web"] = True
        else:
            # Unknown/shared build and configuration changes fail open to coverage.
            selected["api"] = selected["core"] = selected["web"] = True
            selected["containers"] = True
    return selected


def git(*args):
    return subprocess.check_output(["git", *args])


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("Expected a full Git commit SHA")
    return value


def changed_paths(event_name, event):
    if event_name == "workflow_dispatch":
        return None, None, None
    if event_name == "pull_request":
        base = sha(event["pull_request"]["base"]["sha"])
        head = sha(event["pull_request"]["head"]["sha"])
        diff_base = git("merge-base", base, head).decode().strip()
    elif event_name == "push":
        base, head = sha(event["before"]), sha(event["after"])
        if base == "0" * 40:
            return None, None, None
        diff_base = base
    else:
        raise ValueError(f"Unsupported event: {event_name}")
    # Keep the current base for documentation merge-snapshot validation;
    # classify only changes since PR divergence (or the push's before commit).
    output = git("diff", "--name-only", "--no-renames", "-z", diff_base, head)
    return base, diff_base, [p.decode("utf-8") for p in output.split(b"\0") if p]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    if args.base:
        base = git("rev-parse", "--verify", f"{args.base}^{{commit}}").decode().strip()
        diff_base = git("merge-base", base, args.head).decode().strip()
        output = git("diff", "--name-only", "--no-renames", "-z", diff_base, args.head)
        paths = [p.decode("utf-8") for p in output.split(b"\0") if p]
    else:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        base, diff_base, paths = changed_paths(os.environ["GITHUB_EVENT_NAME"], event)
    selected = {key: True for key in CATEGORIES} if paths is None else classify(paths)
    # Exercise these selectors/checkers whenever their implementation changes.
    selected["tooling"] |= selected["docs"]
    selected["docs"] |= selected["tooling"]
    report = {"base": base, "diff_base": diff_base, "changed_files": None if paths is None else len(paths), **selected}
    print(json.dumps(report, indent=2))
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            for key, value in selected.items():
                out.write(f"{key}={str(value).lower()}\n")
            out.write(f"base={base or ''}\n")
            out.write(f"diff_base={diff_base or ''}\n")
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
            out.write("## Applicable checks\n\n")
            for key, value in selected.items():
                out.write(f"- {key}: {'run' if value else 'not applicable to this diff'}\n")


if __name__ == "__main__":
    main()
