"""Offline documentation checks; baseline/historical exceptions stay visible."""

import argparse
from collections import Counter
from functools import lru_cache
import html
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit

from jsonschema import validators
from jsonschema.exceptions import SchemaError
from markdown_it import MarkdownIt
from referencing import Registry
from referencing.exceptions import NoSuchResource
import yaml


MARKDOWN = MarkdownIt("commonmark")
NOTICE = re.compile(r"^> \*\*(?:Historical|Supporting|Generated|Tool-consumed)", re.I)
RELEASE_SCHEMA = "docs/quality/release-scorecard.schema.json"


def deny_remote_schema(uri):
    raise NoSuchResource(ref=uri)


class Snapshot:
    def __init__(self, root, revision=None):
        self.root = Path(root)
        self.revision = revision
        command = ["ls-tree", "-r", "--name-only", "-z", revision] if revision else [
            "ls-files", "-z", "--cached", "--others", "--exclude-standard"
        ]
        self.paths = set(self.git(*command).decode().strip("\0").split("\0")) - {""}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args])

    def exists(self, path):
        return path in self.paths or any(p.startswith(path.rstrip("/") + "/") for p in self.paths)

    @lru_cache(maxsize=None)
    def text(self, path):
        if self.revision:
            return self.git("show", f"{self.revision}:{path}").decode("utf-8")
        return (self.root / path).read_text(encoding="utf-8")


def active_text(text):
    """Check historical successor notices, preserve dated bodies as historical."""
    if NOTICE.match(text.lstrip()):
        heading = re.search(r"(?m)^#{1,6} ", text)
        return text[:heading.start()] if heading else text
    return text


def inline_text(token):
    return "".join(
        child.content for child in token.children or []
        if child.type in ("text", "code_inline", "image")
    )


@lru_cache(maxsize=512)
def anchors(text):
    result, seen = set(), Counter()
    tokens = MARKDOWN.parse(text)
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            title = inline_text(tokens[index + 1])
            slug = re.sub(r"[^\w\s-]", "", title.lower()).replace(" ", "-")
            count = seen[slug]
            seen[slug] += 1
            result.add(slug if not count else f"{slug}-{count}")
    for match in re.finditer(r"\b(?:id|name)\s*=\s*['\"]([^'\"]+)['\"]", text):
        result.add(html.unescape(match[1]))
    return result


def links(text):
    for token in MARKDOWN.parse(text):
        if token.type == "html_block":
            yield from re.findall(r"\b(?:href|src)\s*=\s*['\"]([^'\"]+)['\"]", token.content)
        for child in token.children or []:
            if child.type == "link_open":
                yield child.attrGet("href")
            elif child.type == "image":
                yield child.attrGet("src")
            elif child.type == "html_inline":
                yield from re.findall(r"\b(?:href|src)\s*=\s*['\"]([^'\"]+)['\"]", child.content)


def link_error(snapshot, source, target):
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None  # External links are not contacted or certified.
    path = unquote(parsed.path)
    if path.startswith("/"):
        return "absolute local/host path"
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path)) if path else source
    if resolved == ".." or resolved.startswith("../"):
        return "path outside repository"
    if not snapshot.exists(resolved):
        return "missing path"
    fragment = unquote(parsed.fragment)
    if fragment and resolved in snapshot.paths:
        if resolved.endswith(".md"):
            if fragment not in anchors(snapshot.text(resolved)):
                return "missing Markdown anchor"
        elif re.fullmatch(r"L\d+(?:-L\d+)?", fragment):
            numbers = [int(n) for n in re.findall(r"\d+", fragment)]
            if min(numbers) < 1 or max(numbers) > len(snapshot.text(resolved).splitlines()):
                return "invalid source-line anchor"
    return None


def markdown_failures(snapshot):
    failures, historical = Counter(), 0
    for path in sorted(p for p in snapshot.paths if p.endswith(".md")):
        text = snapshot.text(path)
        selected = active_text(text)
        historical += selected != text
        for target in links(selected):
            error = link_error(snapshot, path, target)
            if error:
                failures[(path, target, error)] += 1
    return failures, historical


def manifest_structure(payload):
    """Read the manifest's own version and mandatory set, without legacy policy lists."""
    if not isinstance(payload, dict):
        return None, {}, ["context manifest must be a mapping"]
    errors = []
    version = payload.get("version")
    if type(version) is not int or version <= 0:
        errors.append("version must be a positive integer")
        version = None
    groups = payload.get("mandatory_read_groups")
    if not isinstance(groups, list) or not groups:
        errors.append("mandatory_read_groups must exist and be a non-empty list")
        return version, {}, errors
    mandatory = {}
    for group in groups:
        if not isinstance(group, dict):
            errors.append("each mandatory group must be a mapping")
            continue
        identifier = group.get("group")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append("each mandatory group needs a non-empty group identifier")
            continue
        if identifier in mandatory:
            errors.append(f"duplicate mandatory group identifier: {identifier}")
        docs = group.get("docs")
        if not isinstance(docs, list) or not docs:
            errors.append(f"mandatory group {identifier}: docs must be a non-empty list")
            mandatory[identifier] = set()
            continue
        targets = set()
        for doc in docs:
            target = doc if isinstance(doc, str) else doc.get("path") if isinstance(doc, dict) else None
            if not isinstance(target, str) or not target.strip():
                errors.append(f"mandatory group {identifier}: each document needs a non-empty path")
                continue
            if target in targets:
                errors.append(f"mandatory group {identifier}: duplicate document path: {target}")
            targets.add(target)
        mandatory[identifier] = targets
    return version, mandatory, errors


def manifest_errors(snapshot, path, payload, base=None, changed=frozenset()):
    version, mandatory, structural = manifest_structure(payload)
    errors = [f"{path}: {error}" for error in structural]
    for targets in mandatory.values():
        for target in sorted(targets):
            if not snapshot.exists(target):
                errors.append(f"{path}: context path does not exist: {target}")
    if errors or base is None or path not in base.paths:
        return errors
    try:
        base_version, previous, baseline_errors = manifest_structure(yaml.safe_load(base.text(path)))
    except (ValueError, TypeError, yaml.YAMLError) as error:
        return [f"{path}: invalid base context manifest: {error}"]
    if baseline_errors:
        return [f"{path}: invalid base context manifest: {error}" for error in baseline_errors]
    if version < base_version:
        errors.append(f"{path}: version must not decrease (base {base_version}, head {version})")
    removals = []
    for identifier in sorted(previous):
        if identifier not in mandatory:
            removals.append(f"mandatory group removed or renamed: {identifier}")
        else:
            for target in sorted(previous[identifier] - mandatory[identifier]):
                removals.append(f"mandatory document removed or renamed in {identifier}: {target}")
    if removals:
        if version <= base_version:
            errors.extend(f"{path}: {removal}; requires a version increase" for removal in removals)
        elif "AGENTS.md" not in changed:
            errors.append(f"{path}: destructive mandatory-set migration requires AGENTS.md in changed paths")
    return errors


def release_schema_errors(schema):
    validator = validators.validator_for(schema)
    validator.check_schema(schema)
    check = validator(schema, registry=Registry(retrieve=deny_remote_schema))
    empty = {
        "scope": "CI schema qualification probe", "revision": "0" * 40,
        "environment": "synthetic/offline", "requirements": ["SEC-001"],
        "evidence": [], "qualification": "pending", "owner_acceptance": "pending",
    }
    errors = []
    if not check.is_valid(empty):
        errors.append("release scorecard must permit an explicitly pending, evidence-free draft")
    for qualification in ("pending", "failed", "verified-for-recorded-scope"):
        accepted = {**empty, "qualification": qualification, "owner_acceptance": "accepted",
                    "acceptance_reference": "synthetic-review-probe"}
        if check.is_valid(accepted):
            errors.append(f"release scorecard accepts empty evidence with owner acceptance ({qualification})")
    qualified = {**empty, "qualification": "verified-for-recorded-scope",
                 "owner_acceptance": "accepted", "acceptance_reference": "synthetic-review-probe",
                 "evidence": [{"locator": "synthetic.txt", "sha256": "0" * 64,
                               "result": "passed", "limits": "synthetic validation probe only"}]}
    if not check.is_valid(qualified):
        errors.append("release scorecard rejects an evidenced, qualified acceptance record")
    return errors


def structural_errors(head, changed, base=None):
    errors = []
    context = "docs/context/CONTEXT_MANIFEST.yaml"
    if context not in head.paths:
        errors.append(f"{context}: mandatory context manifest is missing")
    selected = (changed | {context}) & head.paths
    for path in sorted(selected):
        if not path.startswith("docs/") or not path.endswith((".json", ".yaml", ".yml")):
            continue
        try:
            payload = json.loads(head.text(path)) if path.endswith(".json") else yaml.safe_load(head.text(path))
            if path.endswith(".schema.json"):
                validators.validator_for(payload).check_schema(payload)
            if path == "docs/context/CONTEXT_MANIFEST.yaml":
                errors.extend(manifest_errors(head, path, payload, base=base, changed=changed))
        except (ValueError, TypeError, AttributeError, SchemaError, yaml.YAMLError) as error:
            errors.append(f"{path}: invalid structured documentation: {error}")
    if RELEASE_SCHEMA in head.paths:
        try:
            errors.extend(release_schema_errors(json.loads(head.text(RELEASE_SCHEMA))))
        except Exception as error:
            errors.append(f"{RELEASE_SCHEMA}: schema validation failed: {error}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--worktree", action="store_true")
    args = parser.parse_args()
    head = Snapshot(args.repo, None if args.worktree else args.head)
    base = Snapshot(args.repo, args.base) if args.base else None
    failures, historical = markdown_failures(head)
    baseline, _ = markdown_failures(base) if base else (Counter(), 0)
    novel = failures - baseline
    if base:
        command = ["diff", "--name-only", "--no-renames", "-z", args.base]
        if not args.worktree:
            command.append(args.head)
        changed = set(head.git(*command).decode().strip("\0").split("\0"))
        if args.worktree:
            changed.update(head.git("ls-files", "--others", "--exclude-standard", "-z").decode().strip("\0").split("\0"))
    else:
        changed = head.paths
    errors = structural_errors(head, changed, base=base)
    print(f"Markdown files: {sum(p.endswith('.md') for p in head.paths)}")
    print(f"Historical bodies excluded; successor notices checked: {historical}")
    print(f"Existing active link failures retained: {sum((failures & baseline).values())}")
    print(f"New active link failures: {sum(novel.values())}")
    print("External URLs were not fetched. Baseline exceptions are not a claim of full documentation qualification.")
    for (path, target, error), count in sorted(novel.items()):
        print(f"ERROR {path}: {target}: {error} ({count})")
    for error in errors:
        print(f"ERROR {error}")
    raise SystemExit(bool(novel or errors))


if __name__ == "__main__":
    main()
