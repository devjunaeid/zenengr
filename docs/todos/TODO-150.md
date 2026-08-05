---
id: TODO-150
title: Date + time format dropdowns in settings
feature: FEAT-014
story: US-055
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-145]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-150 - Date + time format dropdowns in settings

## Description

In Settings -> Configuration, date format and time format rows become dropdowns with live demo labels (e.g. "YYYY-MM-DD - 2026-08-05" for date format; 12h/24h for time format). Currency stays ISO code text (validated), timezone stays IANA text (validated).

## Acceptance criteria

- [x] Date format row is a dropdown with live demo labels (e.g. "YYYY-MM-DD - 2026-08-05"). (FR-14.4)
- [x] Time format row is a dropdown (12h/24h). (FR-14.5)
- [x] Currency ISO code text input validated. (FR-14.5)
- [x] Timezone IANA text input validated. (FR-14.5)

## Notes

- Configuration rows live in the Settings tabs layout from FEAT-013. (FR-14.4)
- Shipped 2026-08-05: date_format + time_format dropdowns in Settings -> Configuration with live demo labels; currency (ISO) + timezone (IANA) stay validated text inputs.
