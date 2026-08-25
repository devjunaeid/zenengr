---
id: TODO-190
title: Statement invoice PDF layout in reportlab service
feature: FEAT-019
story: US-064
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-188, TODO-189]
blocks: [TODO-191, TODO-192]
created: "2026-08-26"
updated: "2026-08-26"
---

# TODO-190 — Statement invoice PDF layout in reportlab service

## Description

Enhance `backend/app/services/pdf.py` to support statement-style layout:
- Chronological table for services (Date, Description, Qty, Unit Price, Amount).
- Chronological entries or sub-table for Payments/Advances (Date, Method/Ref, Amount).
- Summary footer block: Total Charges, Total Paid, Balance Due ($\max(\text{Charges} - \text{Paid}, 0)$), Advance Credit ($\max(\text{Paid} - \text{Charges}, 0)$).
- Tenant branding (logo, theme color, currency code, date formats).

## Acceptance criteria

- [ ] Clear, professional PDF output with clean table alignment.
- [ ] Displays charges, payments, due, and advance balances accurately.
- [ ] Safe WinAnsi/Helvetica formatting with currency codes.
