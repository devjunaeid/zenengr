---
id: TODO-079
title: Invoice number generator (tenant-scoped sequential)
feature: FEAT-008
story: US-031
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-075, TODO-017]
blocks: [TODO-078]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-079 — Invoice number generator (tenant-scoped sequential)

## Description

Implement tenant-scoped gapless sequential invoice number generator. Respects tenant's configured format template (FR-2.4). Uses DB sequence or counter table per tenant.

## Acceptance criteria

- [x] InvoiceNumberSequence table: tenant_id, last_number, format_template.
- [x] On issue: next_number = last_number + 1, formatted per tenant's format setting.
- [x] Format template supports variables: {year}, {seq} (zero-padded), {tenant_prefix}.
- [x] Generator is transactional (locked via SELECT FOR UPDATE or row-level lock) to prevent duplicates.
- [x] Counter per tenant ensures scoped sequentiality.

## Notes

InvoiceNumberSequence table (tenant_id PK, last_number, format_template); SELECT FOR UPDATE gapless generator with IntegrityError race retry; tokens {year}/{YYYY}, {seq}/{SEQ}, {seq:0Nd}/{SEQ:0Nd}, {tenant_prefix}; template from tenant setting invoice_number_format with DEFAULT fallback INV-{YYYY}-{SEQ:04d}.
Gapless: gaps may occur if draft deleted after number reservation. Acceptable gap tolerance per US-031 Notes.
