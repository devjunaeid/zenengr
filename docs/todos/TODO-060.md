---
id: TODO-060
title: Template edit warning UI
feature: FEAT-006
story: US-024
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-056]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-060 — Template edit warning UI

## Description

Show warning dialog when editing a service template that has existing project instantiations. Warn that active projects will not be affected.

## Acceptance criteria

- [ ] Service catalog checks if service has been used in any project.
- [ ] If used: show warning banner/before edit confirmation: "Editing this template will not affect existing projects."
- [ ] Warning displayed on service edit page.

## Notes

