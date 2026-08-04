<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as serviceApi from '$lib/api/services.js';
	import MilestoneStepEditor from '$lib/components/MilestoneStepEditor.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	const initial = untrack(() => data.service);

	let name = $state(initial.name);
	let description = $state(initial.description ?? '');
	let defaultPrice = $state(
		initial.default_price !== null && initial.default_price !== undefined
			? String(initial.default_price)
			: ''
	);
	let isActive = $state(initial.is_active);
	/**
	 * @type {Array<{ name: string, expected_duration_days: number|null, description: string|null, _key: string }>}
	 */
	let steps = $state(
		initial.steps.map((s) => ({
			name: s.name,
			expected_duration_days: s.expected_duration_days,
			description: s.description ?? '',
			_key: `s_${s.id}`
		}))
	);
	let busy = $state(false);
	/** @type {string|null} */
	let err = $state(null);

	/**
	 * Strip the client-side `_key` field and renumber to 1..N.
	 */
	function serializeSteps() {
		return steps.map((s, i) => ({
			name: s.name,
			sequence_order: i + 1,
			...(s.expected_duration_days !== null &&
				s.expected_duration_days !== undefined &&
				Number.isFinite(s.expected_duration_days) && {
					expected_duration_days: Number(s.expected_duration_days)
				}),
			...(s.description && s.description.trim() && { description: s.description.trim() })
		}));
	}

	/**
	 * @param {string|number} v
	 */
	function parsePrice(v) {
		if (v === '' || v === null || v === undefined) return null;
		const n = typeof v === 'string' ? Number(v) : v;
		return Number.isFinite(n) ? n : null;
	}

	async function submit() {
		err = null;
		if (steps.some((s) => !s.name.trim())) {
			err = 'Every step needs a name.';
			return;
		}
		busy = true;
		try {
			/** @type {Record<string, any>} */
			const body = {
				name: name.trim(),
				description: description.trim() ? description.trim() : null,
				default_price: parsePrice(defaultPrice),
				is_active: isActive,
				steps: serializeSteps()
			};
			await serviceApi.updateService(fetch, token, initial.id, body);
			goto(resolve('/app/services/[id]', { id: initial.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Edit {initial.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/services')} class="hover:text-indigo-600">Services</a>
		</li>
		<li aria-hidden="true">/</li>
		<li>
			<a href={resolve('/app/services/[id]', { id: initial.id })} class="hover:text-indigo-600"
				>{initial.name}</a
			>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">Edit</li>
	</ol>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">Edit service</h1>

{#if err}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{err}
	</p>
{/if}

{#if initial.in_use}
	<div
		role="alert"
		class="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
	>
		This service is used in {initial.project_count ?? 0}
		{initial.project_count === 1 ? 'project' : 'projects'}. Template edits do not change existing
		project milestones.
	</div>
{/if}

<form
	class="mt-6 max-w-3xl space-y-6"
	onsubmit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<section class="space-y-4">
		<div>
			<label for="s-name" class="block text-sm font-medium text-slate-700">Name *</label>
			<input
				id="s-name"
				type="text"
				bind:value={name}
				required
				maxlength="255"
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>

		<div>
			<label for="s-desc" class="block text-sm font-medium text-slate-700">Description</label>
			<textarea
				id="s-desc"
				bind:value={description}
				rows="3"
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			></textarea>
		</div>

		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<label for="s-price" class="block text-sm font-medium text-slate-700">
					Default price (USD)
				</label>
				<input
					id="s-price"
					type="number"
					step="0.01"
					min="0"
					bind:value={defaultPrice}
					placeholder="0.00"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div class="flex items-end pb-1">
				<label class="inline-flex items-center gap-2 text-sm text-slate-700">
					<input
						type="checkbox"
						bind:checked={isActive}
						class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
					/>
					Active (available for new projects)
				</label>
			</div>
		</div>
	</section>

	<section
		class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
		aria-labelledby="steps-h"
	>
		<div class="flex items-center justify-between">
			<h2 id="steps-h" class="text-base font-semibold text-slate-900">Milestone steps</h2>
			<span class="text-sm text-slate-500">
				{steps.length}
				{steps.length === 1 ? 'step' : 'steps'}
			</span>
		</div>
		<p class="mt-1 text-sm text-slate-500">
			Reorder with the arrow buttons. Sequence is saved as 1..N.
		</p>
		<div class="mt-4">
			<MilestoneStepEditor bind:steps />
		</div>
	</section>

	<div class="flex items-center gap-3 pt-2">
		<button
			type="submit"
			disabled={busy}
			aria-busy={busy}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
			Save changes
		</button>
		<a
			href={resolve('/app/services/[id]', { id: initial.id })}
			class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Cancel
		</a>
	</div>
</form>
