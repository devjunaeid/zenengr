---
id: TODO-199
story: US-066
feature: FEAT-021
status: done
priority: P1
assignee: ""
created: "2026-09-09"
updated: "2026-09-09"
---

# TODO-199 — Frontend new invoice create form: Type selector, Billed-To form card, and searchable project picker

## Context

On `/app/invoices/new`, users need a clean, intuitive way to choose between creating a Project Invoice and a General Invoice. For General Invoices, users need to supply Billed-To information (with an optional quick-fill from existing clients). For Project Invoices, users need a fast, searchable combobox to pick a project.

## Acceptance criteria

- [x] New invoice view features a prominent segmented control for Invoice Type: "Project Invoice" and "General Invoice".
- [x] General Invoice mode displays Billed-To card (Name, Email, Phone, Address, Tax ID) and optional quick-select existing client dropdown.
- [x] Project Invoice mode displays a searchable project combobox with real-time text query filtering and clear selection button.
- [x] Submitting either invoice type sends correct payload to API (`project_id` for project invoices, `billed_to` for general invoices).
