# UI/UX Specification

> This file holds framework-agnostic defaults. No design system exists yet — refine these tokens
> and add page-by-page notes _before_ frontend implementation of any PRD-driven feature
> (per `Agent.md` workflow).

## Design system

- **Color palette:** TBD — default to Tailwind v4's theme tokens (`--color-*`), overridden via `layout.css`.
  Suggested semantic mappings:
  - `primary`, `primary-foreground` — primary actions
  - `secondary`, `secondary-foreground`
  - `muted`, `muted-foreground` — secondary text
  - `destructive` — errors
  - `border`, `input`, `ring`
- **Typography:** System font stack default (Tailwind). Brand fonts TBD.
  - Sizes use Tailwind text scale; weights 400/500/600/700.
- **Spacing scale:** 4px grid (`gap-1` = 4px) — Tailwind v4 defaults.
- **Corner radius:** default `--radius: 0.5rem`; tight controls `rounded-md` (0.375rem), cards `rounded-lg` (0.5rem).
- **Shadows / elevations:** Tailwind `shadow-sm/md/lg/xl`; elevate modals and dropdowns.

## Component library

- **Library:** bits-ui (headless primitives) + Tailwind-styled wrappers co-located in `src/lib/components/`.
- **Core components to build/adopt:** Button, Input, Label, Field, Card, Modal (Dialog), Toast, Tooltip,
  Dropdown, Select, Tabs, Table, Skeleton/Spinner.
- Pattern: bits-ui primitive inside a thin `.svelte` wrapper that applies Tailwind styles and our tokens; consumers import the wrapper.

## Layout

- **Breakpoints:** Tailwind defaults — `sm: 640`, `md: 768`, `lg: 1024`, `xl: 1280`, `2xl: 1536`.
- **Max content width:** `max-w-7xl` (1280px) for app shells; article-style pages `max-w-3xl` (768px).
- **Navigation pattern:** TBD (likely top nav + sidebar once dashboard feature is defined).

## Interactions

- **Loading states:** Skeletons for data-dense areas; spinners for short actions; `disabled` + `aria-busy` on buttons during submit.
- **Empty states:** Provide headline + helpful copy + primary CTA in list/index views.
- **Error states:** Inline (form fields) + toast (network-level) — never silent.
- **Form validation:** Client hints via HTML + ARIA; server is source of truth; surface `details` per field.
- **Toast / notification:** Centered-top or bottom-right stack; auto-dismiss after ~6s; persist error toasts.

## Accessibility

- **Target WCAG level:** 2.1 AA.
- **Focus management:** Visible focus ring via `:focus-visible` (Tailwind `focus-visible:ring`); trap focus in modals/drawers; restore focus on close.
- **ARIA conventions:** Use bits-ui primitives' built-in ARIA; never override without reason; label all controls.
- **Keyboard navigation:** All interactive elements reachable via Tab; Escape closes overlays; Enter/Space activates.
- **Color contrast:** Text on backgrounds ≥ 4.5:1; large text ≥ 3:1.

## Page-by-page notes

> No product pages defined yet (PRD pending). Add a section per page once features are scoped:

### Page: _(template)_

- **Purpose:**
- **Key elements:**
- **User flow:**
- **Wireframe / notes:**
- **States:** loading / empty / error / success
- **Accessibility notes:**