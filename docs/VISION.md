# Vision

Last updated: 2026-03-20

Rocco's HyperTrophy is a deterministic hypertrophy coaching system, not a document viewer and not a chatbot wrapper.

## Two First-Class Modes

- `authored`
  The user selects a fully authored program. These programs remain real selectable products in the app. The app must administer them faithfully and preserve their structure, progression, and philosophy.
- `optimized_generated`
  The user chooses "Choose for me". The app eventually assesses the user and generates a fully customized hypertrophy plan using compiled doctrine, ontology, policy, and user state.

## Canonical Knowledge Source

- `/reference` is the canonical hypertrophy knowledge corpus.
- It contains the PDFs, spreadsheets, authored programs, specialization materials, and technique materials the system is allowed to learn from.
- `docs/guides/*` are deterministic intermediate build artifacts derived from `/reference`. They are useful for build-time inspection, but they are not the canonical source of truth.
- Runtime must never read raw `/reference`.
- Runtime must consume only compiled artifacts.

## Runtime Principles

- Runtime must remain deterministic.
- Runtime must not depend on a paid LLM.
- LLMs may be used only as optional offline development helpers for extraction or organization.
- Core generation, adaptation, and explanation should eventually be able to run locally or offline from compiled artifacts with no cloud dependency.

## What Makes This Product Different

- It combines authored-program fidelity with true generated coaching in one system.
- It is grounded in a canonical corpus instead of freeform AI guessing.
- It should exceed the value of any single source by synthesizing the corpus through explicit doctrine plus explicit system coaching policy.
- It should be able to explain why it chose a split, exercise, volume change, or specialization move without hiding behind a black box.

## Long-Term Destination

- Authored programs remain first-class products.
- Generated mode becomes a true doctrine-driven hypertrophy coaching engine.
- The engine eventually supports generated `Full Body`, `Upper/Lower`, `PPL`, and "best split for me".
- The app adapts over time based on performance, recovery, adherence, weak points, and constraints while staying grounded, deterministic, and explainable.
