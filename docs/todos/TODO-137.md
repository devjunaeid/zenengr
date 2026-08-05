---
id: TODO-137
title: Auto-provisioning of root folders
feature: FEAT-012
story: US-049
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-125]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-137 — Auto-provisioning of root folders

## Description

Provision gallery root folders automatically: "My files" (USER), "Team files" (TENANT), "Project files" (PROJECT) per tenant, and one subfolder per project under "Project files" on project creation. Root folders non-deletable; provisioning idempotent.

## Acceptance criteria

- [x] Root folders auto-created per tenant: My files, Team files, Project files. (FR-12.4)
- [x] One subfolder per project under Project files on project creation. (FR-12.4)
- [x] Root folders non-deletable. (FR-12.4)
- [x] Idempotent provisioning (no duplicates on rerun). (FR-12.4)

## Notes

- Wired into tenant creation and project creation flows.
- Auto roots My files (virtual) / Team files / Project files (+ per-project subfolder) provisioned lazily, idempotent.
