# Code Review Checklist

Run after implementation and before marking a task complete.

## Correctness

- [ ] Feature matches acceptance criteria.
- [ ] Edge cases handled.
- [ ] Errors are caught and surfaced appropriately.
- [ ] No hardcoded secrets or credentials.

## Architecture

- [ ] Code follows frontend or backend standard.
- [ ] Business logic separated from UI / controllers.
- [ ] No duplicated logic; reusable utilities extracted.
- [ ] Naming is clear and consistent.

## Quality

- [ ] No obvious security issues (input validation, XSS, injection, auth).
- [ ] No performance regressions (N+1 queries, large re-renders, blocking calls).
- [ ] Types are accurate; no `any` workarounds without reason.
- [ ] Tests added or updated for new behavior.

## UI/UX

- [ ] Matches `docs/ui-ux-spec.md`.
- [ ] Responsive and accessible.
- [ ] Loading/error/empty states handled.

## Documentation

- [ ] `docs/progress.md` updated.
- [ ] Complex logic has inline comments where needed.
- [ ] API changes reflected if applicable.
