# Release and milestone qualification

Active qualification procedure under [constitution](../governance/constitution.md); technical test mechanisms remain Proposed. [Roadmap](../roadmap/milestones.md) controls package scope. No M0–M6 release is owner accepted here.

For the changed/enabled scope, record controlling requirements/ADRs, revision/source/rule hashes, environment and disposable target, automated results including failures, manual journey, deviations, reviewer and separate owner acceptance. Apply mode/source/history/security/data-safety invariants to every affected release; do not turn unrelated future feature ideas into blockers or treat a historical pass as current evidence.

Applicable gates include Authored field/relationship/consent negatives, effective occurrence/retry/correction integrity, completed exposure and actual dates where enabled, normalized deterministic generation, credential/session/configuration boundaries, PostgreSQL concurrency/migrations where relevant, build/types and honest failure propagation, and device/accessibility/restore evidence for the chosen release scope. SQLite does not qualify PostgreSQL. A dump does not prove restore; a bundle report does not prove device performance.

Classify each failing expectation as confirmed defect, obsolete/conflicting protection, fixture/environment issue or unresolved; retain originals and replace obsolete checks with controlling-contract protection. Checked legacy release rows remain original observations and may be internally contradictory; they cannot close current gates. [Legacy checklist](../implementation/RELEASE_CHECKLIST.md) and [trust model](../architecture/TRUST_AND_MATURITY_MODEL.md) are supporting history only.

The [documentation scorecard schema](release-scorecard.schema.json) records claim/evidence/acceptance metadata without invented physiological scores or thresholds. The [legacy numeric template](../validation/release_scorecard_template.json) remains an illustrative historical artifact, not a measured result or active gate. Evidence retention/access and unresolved qualification are tracked through the [evidence registry](../evidence/README.md).
