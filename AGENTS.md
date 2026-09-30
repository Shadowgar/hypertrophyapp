# AGENTS.md

## Purpose and active context

Mandatory guardrails for agents in this repository. Start from [docs/README.md](docs/README.md), the [product contract](docs/requirements/product-contract.md), [constitution](docs/governance/constitution.md) and [AI working rules](docs/governance/ai-working-rules.md). The documentation authority baseline was owner-approved on 2026-09-28; product requirements, Proposed mechanisms, implementation, verification and release acceptance remain distinct.

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

Follow [DB_SAFETY_LOCK.md](DB_SAFETY_LOCK.md). Before tests/imports/startup/DDL use explicit verified disposable targets and isolated environment; never trust inherited DB/Compose defaults or a fresh container. Production checkout/data/config/services/deployment, secrets/private keys/logs/personal records and source licensing require their own authorized scope. Approval to draft/integrate docs is not permission to implement, migrate, deploy or merge.

Work within the authorized task scope and preserve unrelated work. Production changes require explicit authorization; deployment authorization is separate from implementation approval. Proposed ADRs/plans and historical checklists do not authorize implementation, production operations or release acceptance.

## Tool and MCP usage policy

- **Authority and selection:** Repository source, active contracts, requirements, ADRs and documentation govern application behavior. External documentation, testing, security, observability and design tools assist but cannot silently override owner-approved decisions. Use the smallest useful tool set; do not ask overlapping tools the same question unless a cross-check matters.
- **Local shell:** Use repository and shell tools for source edits, Git, focused tests, builds, local inspection, Docker/Compose, PostgreSQL CLI, Alembic, migrations and service operations. This production server is also the development environment, but source changes, builds, restarts and deployment remain limited to the task's explicit authorization and the separate deployment boundary above. Never wipe/reset/reseed the live database, delete real workout history, treat production persistence as disposable, run destructive migrations casually, or print secrets. Use verified disposable databases/environments for destructive tests, migration rehearsals, concurrency tests and qualification.
- **GitHub:** Inspect branches, commits, PRs, review threads, issues, CI/workflows, mergeability and Dependabot/security state directly. Do not ask the owner to relay status Codex can inspect.
- **Context7:** Use for current third-party library/framework documentation, including Next.js, FastAPI, Starlette, SQLAlchemy, Alembic, React, Playwright and dependency APIs. It does not define this app's architecture or requirements. Never expose Context7 or other API keys in chat, tool output, logs, commits or documentation.
- **Playwright:** Standard browser qualification for significant UI changes to login, Today, Week, history, workout logging, undo/correction, substitutions, scheduling, navigation and responsive/mobile behavior. Check rendered content, interactions, navigation, stale state, console/runtime errors and desktop/mobile viewports as relevant. Supplement rather than replace focused unit/API tests.
- **Codex Security:** Use for security-sensitive implementation and qualification, vulnerability investigation, auth/authorization and secret analysis, especially changes to credentials, file handling, SQL/database boundaries, request parsing, dependencies or externally reachable surfaces. Do not invoke it for every trivial edit.
- **Figma:** Use only for intentional design/UI/UX work; repository implementation and accepted design decisions remain authoritative.
- **PostHog:** Use only for approved analytics, telemetry, flags and error observability. Do not collect performed weights/reps, pain flags, health/readiness answers, body measurements or private notes by default; detailed sensitive telemetry requires an explicit privacy design. Prefer coarse events such as `workout_opened`, `workout_started`, `set_logged`, `set_undone`, `substitution_prompted`, `substitution_confirmed`, `workout_completed`, `schedule_generated`, `schedule_infeasible`, `client_error` and `api_error`. Review telemetry schemas explicitly before implementation.
- **Cloudflare:** Use for deployment-edge DNS, proxy, WAF/firewall, TLS, rate limiting and origin protection, not application-domain logic.
- **No duplicate systems:** GitHub Issues and repository documentation are project tracking/decision authority. Do not copy planning or specifications into Linear, Notion, Airtable or another external system unless requested, or add live PostgreSQL database-management MCP access for convenience; use authorized shell/Docker/PostgreSQL tools.

Route repository questions to the repository, PR/CI questions to GitHub, third-party API questions to Context7, browser behavior to Playwright, security questions to Codex Security, database/container operations to local tools, design work to Figma and approved telemetry work to PostHog. Avoid calls that do not materially improve correctness.
