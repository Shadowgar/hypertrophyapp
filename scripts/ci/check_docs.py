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


def manifest_errors(snapshot, path, payload):
    errors = []
    for group in payload.get("mandatory_read_groups", []):
        for doc in group.get("docs", []):
            target = doc if isinstance(doc, str) else doc.get("path")
            if not isinstance(target, str) or not snapshot.exists(target):
                errors.append(f"{path}: context path does not exist: {target}")
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


def structural_errors(head, changed):
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
                errors.extend(manifest_errors(head, path, payload))
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
    errors = structural_errors(head, changed)
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
