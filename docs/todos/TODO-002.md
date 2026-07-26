---
id: TODO-002
title: Author backend Dockerfile + .dockerignore + uvicorn entrypoint
feature: FEAT-001
story: US-002
status: done
priority: high
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-003]
created: "2026-07-25"
updated: "2026-07-25"
---

# TODO-002 — Author backend Dockerfile + .dockerignore + uvicorn entrypoint

## Description

Create `backend/Dockerfile` (Python 3.14, `uv sync`, run FastAPI `[standard]` via `uvicorn` on
`0.0.0.0:8000`) and `backend/.dockerignore` (exclude `.venv`, `__pycache__`, `.pytest_cache`, `.env*`).
Confirm FastAPI entry module name once backend source exists.

## Acceptance criteria

- [ ] `backend/Dockerfile` builds successfully (`docker build backend/`).
- [ ] Container starts API on `0.0.0.0:8000`; `/docs` reachable.
- [ ] `DATABASE_URL` and `REDIS_URL` are read by the app.
- [ ] `.dockerignore` excludes caches and secrets.
- [ ] Reviewed against `docs/backend-standard.md`.

## Notes