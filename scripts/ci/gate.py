"""Aggregate job results without converting a required skip/failure into a pass."""

import json
import os


JOBS = {
    "docs": ("documentation",),
    "tooling": ("workflow-checks",),
    "api": ("api-tests",),
    "core": ("core-tests",),
    "web": ("web-checks",),
    "containers": ("container-build",),
}


def evaluate(needs):
    errors = []
    changes = needs["changes"]
    if changes["result"] != "success":
        errors.append("Changed-file classification did not succeed")
    for category, jobs in JOBS.items():
        flag = changes.get("outputs", {}).get(category)
        if flag not in ("true", "false"):
            errors.append(f"Missing or invalid applicability output: {category}")
        required = flag == "true"
        for job in jobs:
            result = needs[job]["result"]
            if required and result != "success":
                errors.append(f"{job}: required for this diff, result={result}")
            elif not required and result not in ("success", "skipped"):
                errors.append(f"{job}: unexpected result={result}")
    return errors


if __name__ == "__main__":
    needs = json.loads(os.environ["CI_NEEDS"])
    errors = evaluate(needs)
    report = "\n".join(f"- {job}: {data['result']}" for job, data in needs.items())
    print(report)
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
            out.write("## CI qualification\n\n" + report + "\n")
    for error in errors:
        print(f"::error::{error}")
    raise SystemExit(bool(errors))
