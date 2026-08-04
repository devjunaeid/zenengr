---
id: TODO-011
title: Logo and branding field support
feature: FEAT-001
story: US-006
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-010]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-011 — Logo and branding field support

## Description

Add logo upload/URL field and branding fields (primary color, secondary color) to tenant profile. Logo appears on invoice PDFs and portal header.

## Acceptance criteria

- [x] Logo upload endpoint stores image URL.
- [x] Branding color fields stored on tenant model.
- [x] Logo renders in portal header and invoice PDF template.
- [x] File type/size validation on upload.

## Notes

Logo upload endpoint POST /tenant/branding/logo (image/* validation, 2MB cap, saved to /uploads, sets branding.logo_url), header logo render (settings upload + header img), invoice PDF branding (color + logo via onFirstPage/ImageReader), file validation + tests (test_branding_api.py).
