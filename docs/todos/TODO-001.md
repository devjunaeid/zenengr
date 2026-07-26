---
id: TODO-001
title: Author frontend Dockerfile + .dockerignore
feature: FEAT-001
story: US-001
status: done
priority: high
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-003]
created: "2026-07-25"
updated: "2026-07-25"
---

# TODO-001 — Author frontend Dockerfile + .dockerignore

## Description

Create `frontend/Dockerfile` (Node LTS, `npm install`, `npm run build`, expose preview port `4173`)
and `frontend/.dockerignore` (exclude `node_modules`, `.svelte-kit`, `build`, `.env*`).

## Acceptance criteria

- [ ] `frontend/Dockerfile` builds successfully (`docker build frontend/`).
- [ ] Built image serves the SvelteKit preview server on `4173`.
- [ ] `.dockerignore` excludes build artifacts and secrets.
- [ ] Reviewed against `docs/frontend-standard.md`.

## Notes