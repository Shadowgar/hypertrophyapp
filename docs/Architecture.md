# Architecture - Adaptive Coaching Target State

Last updated: 2026-03-06

## Runtime Boundary

Runtime reads only:
- canonical program templates
- canonical coaching rules
- exercise catalog
- user training state

Runtime does not read raw `reference/*.pdf` or `reference/*.xlsx`.
Runtime does not depend on `docs/guides/generated/*.md` text artifacts.

## Runtime Components

1. Template Runtime Service
- Resolves active program/phase/week/day
- Delivers ordered exercise slots and prescriptions

2. Rules Runtime Service
- Loads typed coaching rules per program scope
- Evaluates progression, fatigue, deload, transition, substitution decisions

3. Exercise Catalog Service
- Canonical exercise IDs, aliases, muscles, equipment, default media, substitutions

4. User State Service
- Stores logs and progression state
- Stores fatigue/adherence/stall markers

5. Decision Engine
- Inputs: template + rules + user state
- Outputs: today's plan, post-session evaluation, next-session adaptation

6. API/UI Layer
- Program selection
- Workout execution and logging
- Explainable adaptation timeline

## Build-Time Components

1. Excel importer pipeline -> canonical program objects
2. PDF doctrine distillation pipeline -> typed coaching rules
3. Provenance and quality gates -> verification reports

## Legacy Components To Isolate

- `importers/reference_corpus_ingest.py` generated markdown guides remain build artifacts only.
- `GET /plan/intelligence/reference-pairs` is informational provenance, not coaching runtime logic.

## Deployment Principle

Single-node deployment can remain unchanged (web/api/postgres/caddy). The architecture change is a domain-model and runtime-boundary change, not a hosting change.
