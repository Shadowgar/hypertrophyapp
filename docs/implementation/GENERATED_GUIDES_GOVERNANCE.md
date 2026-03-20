# Generated Guides Governance

Last updated: 2026-03-20

## Purpose

Define how `docs/guides/generated/` artifacts are handled so they cannot be mistaken for contributor authority.

## Policy

1. Generated guides are evidence artifacts, not runtime or implementation authority.
2. Contributors must not use generated guides as first-read docs for active coding decisions.
3. Active decisions must come from:
   - `docs/architecture/*` governing docs
   - `docs/current_state_decision_runtime_map.md`
   - `docs/implementation/*` active rails

## Dedupe and Canonicalization

1. Keep one canonical generated guide per source asset hash when possible.
2. Near-duplicate outputs should be pruned or grouped by provenance hash.
3. If duplicates are retained, annotate why (for example extraction quality comparison).

## Contributor Read Exclusion

During normal implementation, skip `docs/guides/generated/` unless:

- you are debugging importer/provenance extraction behavior, or
- an active doc explicitly points to a generated file as supporting evidence.

## Linking Rule

When a generated guide is cited, pair it with:

- the source asset identity (PDF/XLSX), and
- a canonical runtime artifact or validation doc that consumed the source.
