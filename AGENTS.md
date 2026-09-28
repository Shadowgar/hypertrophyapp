# AGENTS.md

## Purpose and active context

Mandatory guardrails for agents in this repository. Start from [docs/README.md](docs/README.md), the [product contract](docs/requirements/product-contract.md), [constitution](docs/governance/constitution.md) and [AI working rules](docs/governance/ai-working-rules.md). The documentation integration basis is owner approved on 2026-09-28 for this review branch; it is not release acceptance or implementation/deployment approval.

Before sensitive changes, follow [docs/context/CONTEXT_MANIFEST.yaml](docs/context/CONTEXT_MANIFEST.yaml): read the common group, then **only the groups matching every affected area**, in order. Within each area: product/constitution → relevant ADR/status → area contract → runtime authority → requirement/catalog/traceability → current roadmap and registered bounded plan. Read historical material only when an active document explicitly requires a compatibility/provenance question. No blanket legacy-document read requirement remains.

Sensitive areas include Authored program behavior, Customized generation/onboarding/program selection/plan generation, progression/load, scheduling/workout routing, ingestion/source artifacts, exercise metadata/substitution/collision, recommendations, security and database/migrations. Cross-area changes require all affected groups. Unaccepted ADR mechanisms and Proposed plans grant no implementation permission. D-001–D-022 remain preserved decision constraints and cannot be overridden by a Proposed ADR.

## Non-negotiable runtime governance

- Authored Full Body Phase 1 and Authored Full Body Phase 2 remain separate from generated programs.
- Generated programs never overwrite, modify, replace or reinterpret authored templates.
- Core workout/program decisions remain deterministic and auditable; no runtime LLM inference may determine prescriptions. AI may explain, converse, research, summarize, analyze and assist development without prescription mutation authority.
- Raw onboarding answers map into deterministic GenerationProfile before generation consumes them.
- Authored adaptation is working-load authority; source-approved substitutions require explicit confirmation. Constraints grant no unrelated prescription-mutation permission.
- Metadata-v2 scoring remains frozen/no-op; accounting changes are not activation approval.
- Preserve runtime `docs/rules/**`, source/build provenance and licensing; relocation requires separately scoped consumer migration/tests.

## Implementation expectations

For authorized generated/onboarding/progression/routing or other sensitive behavior changes, add/update meaningful behavior and negative-boundary tests; update deterministic decision traces/logging where appropriate. Name the current decision owner/path and actual inputs/outputs; do not overclaim authority or qualification. No presentation/compatibility façade/executor may invent shadow policy or causal explanations. Keep mode, source-slot/performed variant, occurrence/revision, retry/correction and evidence boundaries intact.

Forbidden: silent authored/generated merging, raw answers inside generation, nondeterministic core decisions, source-layout replay presented as original generation, invented explanatory causes, unapproved scoring activation and historical checkmarks promoted to current acceptance.

## Production and data safety

Follow the unchanged [DB_SAFETY_LOCK.md](DB_SAFETY_LOCK.md). Before tests/imports/startup/DDL use explicit verified disposable targets and isolated environment; never trust inherited DB/Compose defaults or a fresh container. Production checkout/data/config/services/deployment, secrets/private keys/logs/personal records and source licensing require their own authorized scope. Approval to draft/integrate docs is not permission to implement, migrate, deploy or merge.

For this documentation integration, work only in the separate documentation review worktree; documentation commit/publication on the existing review branch is authorized. No application/runtime/workflow/packaging/rule/source-artifact changes, production tests/services/builds/installations/migrations, production checkout/branch changes, main merge, PR, WSL rebase repair or subagents. Leave the pre-existing debug-log modification untouched. Stop after publication for owner review.
