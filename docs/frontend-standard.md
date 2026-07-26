# Frontend Standard

## Framework / stack

- Framework: SvelteKit 2 (Svelte 5, runes mode enforced via `vite.config.js`)
- Language: JavaScript with JSDoc (no TypeScript) — per `frontend/AGENTS.md`
- Styling: Tailwind CSS v4 (via `@tailwindcss/vite`)
- Tailwind addons: `@tailwindcss/forms`, `@tailwindcss/typography`
- Components: bits-ui
- State: Svelte runes (`$state`, `$derived`, `$effect`) and Svelte stores where appropriate
- Data fetching: SvelteKit `load` functions and `event.fetch`; route-level `+page.server.js` / `+layout.server.js`
- Forms: TBD (validate on the server; client hints via HTML validation + bits-ui form primitives)
- Testing: TBD — none configured yet (pending PRD; candidates: vitest, @testing-library/svelte, playwright)

## Project structure

Live layout (detected under `frontend/`):

```text
frontend/
  src/
    app.d.ts          # Ambient types (SvelteKit-generated)
    app.html          # HTML shell
    lib/              # Reusable modules, components, utilities
      index.js
      assets/
    routes/           # File-based routes (SvelteKit)
      +layout.svelte
      +page.svelte
      layout.css      # Tailwind entry imported by root layout
  static/             # Static assets served as-is
  vite.config.js
  eslint.config.js
  prettier.config.js
  jsconfig.json       # Path/config for svelte-check
  package.json
```

Conventions to follow going forward:

```text
src/
  routes/          # File-based routes / pages
  lib/
    components/    # Reusable .svelte components
    actions/       # Form actions / shared logic
    server/        # Server-only utilities (DB, secrets)
    utils/         # Pure helpers
    api/           # API clients to backend
  types/           # JSDoc typedefs / ambient d.ts
```

## Conventions

- Use runes mode (`$state`, `$derived`, `$effect`) for component state — already enforced in `vite.config.js`.
- Prefer composition over inheritance; keep components single-responsibility.
- Co-locate tests next to source files once a test runner is added.
- Co-locate Tailwind class organization with `layout.css` as the single `@import "tailwindcss"` entrypoint.
- Theming / tokens must follow `docs/ui-ux-spec.md`.
- Keep server-only code under `src/lib/server/*` so it is never shipped to the client bundle.
- All API calls to the FastAPI backend should go through `event.fetch` in `load` functions or a thin `lib/api` client; never call `fetch` in pure client components if data is needed at render.

## Code style

- Formatter: Prettier (`useTabs: true`, `singleQuote: true`, `trailingComma: 'none'`, `printWidth: 100`,
  plugins: `prettier-plugin-svelte`, `prettier-plugin-tailwindcss`, Tailwind stylesheet: `./src/routes/layout.css`)
- Linter: ESLint (`@eslint/js` recommended + `eslint-plugin-svelte` recommended, prettier-compatible)
- Type checker: `svelte-check` (JSDoc path via `jsconfig.json`)
- Use the Svelte MCP `svelte-autofixer` tool before sending any `.svelte` code; use `list-sections` /
  `get-documentation` for Svelte/SvelteKit questions.

## Testing

- _Strategy TBD once test runner is selected._ Desired coverage:
  - Unit tests for utilities and stores.
  - Component tests for interactive UI.
  - E2E tests for critical user flows (Browser/Puppeteer MCP available).

## Commands

Run from `frontend/` (npm):

- Dev server: `npm run dev`
- Build: `npm run build`
- Preview build: `npm run preview`
- Type check: `npm run check`
- Type check (watch): `npm run check:watch`
- Lint: `npm run lint`  (prettier --check . && eslint .)
- Format: `npm run format`  (prettier --write .)
- Prepare (post-install): `npm run prepare`  (svelte-kit sync)