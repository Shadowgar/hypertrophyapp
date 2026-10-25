"""Restore the exact private source for protected-main CI; never publish test bodies.

Only environment-scoped Actions secrets from the owner-approved main workflow supply
PHASE1_SOURCE_B64_1..3. No download credentials, network or workbook parsing here.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

DIGEST = "46f50999771cbb454b325729b2d2a77515dbcf2cdd86891e4543eab65019bb71"
SIZE = 88063
RELATIVE = Path("reference/Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx")
SECRET_NAMES = tuple(f"PHASE1_SOURCE_B64_{index}" for index in (1, 2, 3))


class FixtureError(Exception):
    """Fixed messages only: never include source bytes or environment values."""


def restore(repo: Path, parts: list[str]) -> Path:
    if len(parts) != 3 or any(not part for part in parts):
        raise FixtureError("Private Phase 1 fixture unavailable; owner-approved environment required.")
    encoded = "".join(parts)
    if len(encoded) != 4 * ((SIZE + 2) // 3) or any(len(part) > 40000 for part in parts):
        raise FixtureError("Private Phase 1 fixture encoding rejected.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise FixtureError("Private Phase 1 fixture encoding rejected.") from None
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != DIGEST:
        raise FixtureError("Private Phase 1 fixture checksum rejected.")
    directory = repo / RELATIVE.parent
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise FixtureError("Private fixture directory rejected.")
    directory.mkdir(mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    target = repo / RELATIVE
    # Exclusive creation also rejects an existing file or symlink; never overwrite it.
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise FixtureError("Private fixture destination already exists; refusing overwrite.") from None
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
    except BaseException:
        target.unlink()
        raise
    return target


def summarize(report: Path) -> None:
    """Publish counts and test identifiers, never assertion values or captured output."""
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError):
        print("API test report unavailable; private output was not published.")
        return
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    counts = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    print(f"API: {passed} passed, {counts['failures']} failed, "
          f"{counts['errors']} errors, {counts['skipped']} skipped.")
    for case in root.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            # Names originate in test code; unexpected parameter values are withheld.
            identity = case.attrib.get("classname", "") + "." + case.attrib.get("name", "")
            if re.fullmatch(r"[A-Za-z0-9_.-]{1,240}", identity):
                print("Failed test: " + identity)
            else:
                print("Failed test identifier withheld (parameterized or unexpected characters).")


def main(arguments: list[str]) -> int:
    if not arguments or arguments[0] != "--":
        print("Usage: licensed_phase1.py -- <unchanged pytest arguments>")
        return 2
    repo = Path(__file__).resolve().parents[2]
    target = None
    try:
        # Remove fixture payloads before invoking tests or their children.
        parts = [os.environ.pop(name, "") for name in SECRET_NAMES]
        target = restore(repo, parts)
        del parts
        print("Exact private Phase 1 source verified; raw test output remains private.")
        with tempfile.TemporaryDirectory(prefix="phase1-ci-private-") as private:
            report = Path(private) / "results.xml"
            log = Path(private) / "pytest.log"
            with log.open("xb") as output:
                log.chmod(0o600)
                result = subprocess.run([sys.executable, "-m", "pytest", *arguments[1:],
                                         "--junitxml", str(report)], stdout=output, stderr=subprocess.STDOUT)
            summarize(report)
            return result.returncode
    except FixtureError as error:
        print(str(error))
        return 2
    finally:
        if target is not None:
            target.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
