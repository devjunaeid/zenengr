---
name: svelte5-tailwind-v4
description: Guidelines and patterns for developing frontend components using Svelte 5 (Runes), Tailwind CSS v4, bits-ui, and SvelteKit 2. Use when writing, editing, or refactoring frontend code, UI components, or routes.
---

# Svelte 5 & Tailwind CSS v4 Development Skill

This skill guides development for the project's frontend stack: **Svelte 5** (Runes mode), **SvelteKit 2**, **Tailwind CSS v4** (`@tailwindcss/vite`), and **bits-ui**.

---

## 1. Svelte 5 Runes Rules

Runes mode is strictly enforced. **Do not use legacy Svelte 3/4 syntax.**

### Forbidden vs Required Syntax:

| Legacy Svelte 3/4 (FORBIDDEN) | Svelte 5 Runes (REQUIRED) | Notes |
| :--- | :--- | :--- |
| `export let prop = value;` | `let { prop = value } = $props();` | Props declaration |
| `let count = 0;` (reactive) | `let count = $state(0);` | Reactive state variable |
| `$: doubled = count * 2;` | `let doubled = $derived(count * 2);` | Derived value |
| `$: { ...complex... }` | `let res = $derived.by(() => { ... });` | Complex computed state |
| `$: console.log(x);` / `onMount` | `$effect(() => { ... });` | Side effects (client only) |
| `<slot />` or `<slot name="x" />` | `{#snippet children()}` / `{@render children()}` | Content projection / snippets |
| `<button on:click={fn}>` | `<button onclick={fn}>` | Standard DOM event attributes (`onclick`, `onkeydown`, etc.) |
| `createEventDispatcher()` | Callback props: `let { onchange } = $props();` | Invoke callback prop directly |

### Key Runes Patterns:
```svelte
<script>
  /** @type {{ title: string, initialCount?: number, onchange?: (n: number) => void }} */
  let { title, initialCount = 0, onchange } = $props();

  let count = $state(initialCount);
  let isEven = $derived(count % 2 === 0);

  function increment() {
    count += 1;
    onchange?.(count);
  }

  $effect(() => {
    // Only runs on the client after mount and when dependencies change
    console.log('Count changed:', count);
  });
</script>

<div>
  <h3>{title}</h3>
  <button onclick={increment} class="btn">Count: {count} ({isEven ? 'Even' : 'Odd'})</button>
</div>
```

---

## 2. Tailwind CSS v4 Conventions

Tailwind v4 is configured via `@tailwindcss/vite` without a `tailwind.config.js`.

* **CSS Entrypoint**: `src/routes/layout.css` contains `@import "tailwindcss";`.
* **Custom Themes**: Declared in CSS using `@theme` directives rather than JavaScript configuration files.
* **Component Styling**:
  * Use utility classes directly in `.svelte` markup.
  * Follow Prettier ordering via `prettier-plugin-tailwindcss`.
  * Ensure color tokens and dark/light modes conform to `docs/ui-ux-spec.md`.

---

## 3. Bits UI & Component Composition

* Use `bits-ui` headless primitives for accessible components (dialogs, dropdowns, popovers, tabs, switches).
* Handle state binding using Svelte 5 `bind:open`, `bind:value`, or controlled callback props.
* Example:
```svelte
<script>
  import { Dialog } from 'bits-ui';
  let open = $state(false);
</script>

<Dialog.Root bind:open>
  <Dialog.Trigger class="...">Open Dialog</Dialog.Trigger>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 bg-black/50" />
    <Dialog.Content class="fixed center bg-white p-6 rounded shadow">
      <Dialog.Title class="text-lg font-bold">Dialog Title</Dialog.Title>
      <Dialog.Close class="btn">Close</Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

---

## 4. SvelteKit 2 Routing & Data Loading

* **Data Fetching**:
  * Server-side loads: use `+page.server.js` or `+layout.server.js` with `fetch`.
  * Client calls: Always use `event.fetch` in `load` functions or a thin API wrapper under `src/lib/api/`.
  * Never place raw `fetch()` directly inside component script bodies for initial render data.
* **Server-Only Isolation**:
  * Place secrets, database operations, or server-only logic strictly in `src/lib/server/*`. SvelteKit prevents client imports from this directory.

---

## 5. Verification & Linting

When modifying frontend code:
1. Run syntax/type check: `npm run check` (runs `svelte-check`).
2. Run targeted lint: `npx prettier --check <file>` and `npx eslint <file>`.
3. Do **NOT** run production builds (`npm run build`) for local updates — the dev container uses hot reloading.
