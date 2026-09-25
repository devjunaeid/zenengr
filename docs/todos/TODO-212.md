---
id: TODO-212
story: US-071
feature: FEAT-024
title: Audit and optimize backend queries and API payloads for lean default responses
status: done
priority: P1
dependencies: []
blocks: []
---

# TODO-212 - Audit and optimize backend queries and API payloads for lean default responses

## What to do

1. Audit `backend/app/api/v1/projects.py` and `services/projects.py`:
   - Inspect `get_project_overview` and `get_project` queries.
   - Verify that endpoints do not calculate or fetch unused relational trees by default.
2. Audit `backend/app/api/v1/clients.py` and `services/clients.py`:
   - Ensure client detail endpoint does not do heavy unneeded joins.
3. Audit `backend/app/api/v1/invoices.py` and `files.py`:
   - Ensure list queries use proper indexed filters and limit defaults.
4. Run targeted tests to verify backend regression safety.

## Acceptance Check

- Targeted backend tests pass cleanly.
- Endpoints return only necessary fields and execute only required queries.
