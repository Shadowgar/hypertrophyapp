# Working Agreements

## No-Drift Rules
1. Deterministic engine first: no runtime retrieval/search/pdf parsing.
2. Scope changes must update `docs/Master_Plan.md` in the same PR.
3. No broad refactors without explicit plan update and acceptance criteria.
4. Template changes must be versioned in `programs/`.
5. API contract changes must be reflected in web client and docs together.

## Commit Discipline
- Keep commits focused and reversible.
- Include docs with behavior changes.
- Do not mix infra rewrites with feature logic unless unavoidable.

## PR Checklist
- [ ] Runtime determinism preserved.
- [ ] Master Plan updated if scope changed.
- [ ] API and UI contracts aligned.
- [ ] Docker Compose boot path still works.
- [ ] New template/schema changes versioned and documented.

## Decision Record Rule
Major design decisions should be appended to architecture docs with rationale and rollback notes.
