<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as projectApi from '$lib/api/projects.js';
	import * as serviceApi from '$lib/api/services.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { fmtPrice } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);

	let name = $state('');
	let clientId = $state(untrack(() => data.initialClientId));
	/** @type {string|null} */
	let startDate = $state(null);
	/** @type {string|null} */
	let ownerId = $state(null);
	/** @type {string[]} */
	let selectedServiceIds = $state([]);
	let busy = $state(false);
	/** @type {string|null} */
	let err = $state(null);

	let previewOpen = $state(false);
	/** @type {Record<string, import('$lib/api/services.js').MilestoneStep[]|null>} */
	let previewCache = $state({});
	/** @type {Record<string, boolean>} */
	let previewLoading = $state({});
	/** @type {string|null} */
	let previewErr = $state(null);

	let selectedServiceCount = $derived(selectedServiceIds.length);

	$effect(() => {
		// Auto-open preview the first time the user selects any service.
		if (selectedServiceCount > 0) previewOpen = true;
	});

	/**
	 * Fetch service details on demand for each selected service and merge.
	 * Caches in `previewCache` keyed by service id.
	 */
	async function loadPreview() {
		previewErr = null;
		const missing = selectedServiceIds.filter(
			(id) => previewCache[id] === undefined && !previewLoading[id]
		);
		if (missing.length === 0) return;
		// mark loading
		const nextLoading = { ...previewLoading };
		for (const id of missing) nextLoading[id] = true;
		previewLoading = nextLoading;
		try {
			const results = await Promise.all(
				missing.map((id) => serviceApi.getService(fetch, token, id))
			);
			const nextCache = { ...previewCache };
			for (const detail of results) {
				const steps = (detail.steps ?? [])
					.slice()
					.sort((a, b) => a.sequence_order - b.sequence_order);
				nextCache[detail.id] = steps;
			}
			previewCache = nextCache;
		} catch (e) {
			previewErr = e instanceof ApiError ? e.message : 'Could not load milestone preview.';
		} finally {
			const done = { ...previewLoading };
			for (const id of missing) delete done[id];
			previewLoading = done;
		}
	}

	$effect(() => {
		// Reload preview when selection changes and the panel is open.
		if (previewOpen && selectedServiceIds.length > 0) {
			loadPreview();
		}
	});

	/**
	 * @param {string} id
	 */
	function toggleService(id) {
		if (selectedServiceIds.includes(id)) {
			selectedServiceIds = selectedServiceIds.filter((x) => x !== id);
		} else {
			selectedServiceIds = [...selectedServiceIds, id];
		}
	}

	/**
	 * Aggregated step list across selected services. Used to show the
	 * "what will be created" preview on the new-project form.
	 * @type {Array<{ serviceName: string, step: import('$lib/api/services.js').MilestoneStep }>}
	 */
	let aggregatedSteps = $derived.by(() => {
		const out = [];
		for (const sid of selectedServiceIds) {
			const svc = data.services.find((s) => s.id === sid);
			const steps = previewCache[sid] ?? null;
			if (!steps) continue;
			for (const step of steps) {
				out.push({ serviceName: svc?.name ?? 'Service', step });
			}
		}
		return out;
	});

	async function submit() {
		err = null;
		if (!clientId) {
			err = 'Pick a client.';
			return;
		}
		if (selectedServiceIds.length === 0) {
			err = 'Pick at least one service.';
			return;
		}
		busy = true;
		try {
			/** @type {Record<string, any>} */
			const body = {
				name: name.trim(),
				client_id: clientId,
				service_ids: selectedServiceIds
			};
			if (startDate) body.start_date = startDate;
			if (ownerId) body.owner_id = ownerId;
			const created = await projectApi.createProject(fetch, token, /** @type {any} */ (body));
			goto(resolve('/app/projects/[id]', { id: created.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Create failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>New project — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/projects')} class="hover:text-indigo-600">Projects</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">New</li>
	</ol>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">New project</h1>

{#if err}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{err}
	</p>
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
			<label for="p-name" class="block text-sm font-medium text-slate-700">Name *</label>
			<input
				id="p-name"
				type="text"
				bind:value={name}
				required
				maxlength="255"
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>

		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<label for="p-client" class="block text-sm font-medium text-slate-700">Client *</label>
				<select
					id="p-client"
					bind:value={clientId}
					required
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				>
					<option value="" disabled>Select a client</option>
					{#each data.clients as c (c.id)}
						<option value={c.id}>{c.name}</option>
					{/each}
				</select>
				{#if data.clients.length === 0}
					<p class="mt-1 text-xs text-slate-500">
						No active clients. <a
							href={resolve('/app/clients/new')}
							class="text-indigo-600 hover:text-indigo-500">Create one</a
						> first.
					</p>
				{/if}
			</div>
			<div>
				<label for="p-start" class="block text-sm font-medium text-slate-700">Start date</label>
				<input
					id="p-start"
					type="date"
					bind:value={startDate}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
		</div>

		<div>
			<label for="p-owner" class="block text-sm font-medium text-slate-700">Owner</label>
			<select
				id="p-owner"
				bind:value={ownerId}
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			>
				<option value={null}>— Unassigned —</option>
				{#each data.users as u (u.id)}
					<option value={u.id}>{u.full_name} ({u.email})</option>
				{/each}
			</select>
		</div>
	</section>

	<section
		class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
		aria-labelledby="services-h"
	>
		<div class="flex items-center justify-between">
			<h2 id="services-h" class="text-base font-semibold text-slate-900">Services *</h2>
			<span class="text-sm text-slate-500">
				Selected: <span class="font-medium text-slate-700">{selectedServiceCount}</span>
				{selectedServiceCount === 1 ? 'service' : 'services'}
			</span>
		</div>
		<p class="mt-1 text-sm text-slate-500">
			Pick one or more services. Each one creates its milestones on save.
		</p>

		{#if data.services.length === 0}
			<p class="mt-4 text-sm text-slate-500">
				No active services. <a
					href={resolve('/app/settings/services/new')}
					class="text-indigo-600 hover:text-indigo-500">Create one</a
				> first.
			</p>
		{:else}
			<ul class="mt-4 space-y-2" role="group" aria-labelledby="services-h">
				{#each data.services as svc (svc.id)}
					{@const checked = selectedServiceIds.includes(svc.id)}
					<li>
						<label
							class="flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
						>
							<input
								type="checkbox"
								{checked}
								onchange={() => toggleService(svc.id)}
								class="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
							/>
							<span class="flex-1">
								<span class="block text-sm font-medium text-slate-900">{svc.name}</span>
								<span class="mt-0.5 block text-xs text-slate-500">
									{svc.step_count}
									{svc.step_count === 1 ? 'step' : 'steps'}
									{#if svc.default_price}· default {fmtPrice(svc.default_price)}{/if}
								</span>
								{#if svc.description}
									<span class="mt-1 block text-xs text-slate-600">{svc.description}</span>
								{/if}
							</span>
						</label>
					</li>
				{/each}
			</ul>

			{#if selectedServiceCount > 0}
				<div class="mt-4">
					<button
						type="button"
						onclick={() => (previewOpen = !previewOpen)}
						aria-expanded={previewOpen}
						aria-controls="preview-steps"
						class="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="h-4 w-4 transition-transform {previewOpen ? 'rotate-90' : ''}"
							aria-hidden="true"
						>
							<path
								fill-rule="evenodd"
								d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
								clip-rule="evenodd"
							/>
						</svg>
						{previewOpen ? 'Hide' : 'Preview'} milestones ({aggregatedSteps.length})
					</button>
				</div>

				{#if previewOpen}
					<div id="preview-steps" class="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3">
						{#if previewErr}
							<p role="alert" class="text-sm text-red-700">{previewErr}</p>
						{/if}
						{#if aggregatedSteps.length === 0}
							<p class="text-sm text-slate-500">
								{Object.values(previewLoading).some(Boolean) ? 'Loading…' : 'No steps to preview.'}
							</p>
						{:else}
							<ol class="space-y-2">
								{#each aggregatedSteps as item, i (i)}
									<li class="flex items-start gap-2 text-sm text-slate-700">
										<span
											class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
											aria-hidden="true"
										>
											{i + 1}
										</span>
										<span class="flex-1">
											<span class="font-medium text-slate-900">{item.step.name}</span>
											<span class="ml-1 text-xs text-slate-500">({item.serviceName})</span>
											{#if item.step.expected_duration_days}
												<span class="ml-2 text-xs text-slate-500"
													>{item.step.expected_duration_days}d</span
												>
											{/if}
										</span>
									</li>
								{/each}
							</ol>
						{/if}
					</div>
				{/if}
			{/if}
		{/if}
	</section>

	<div class="flex items-center gap-3 pt-2">
		<button
			type="submit"
			disabled={busy}
			aria-busy={busy}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
			Create project
		</button>
		<a
			href={resolve('/app/projects')}
			class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Cancel
		</a>
	</div>
</form>
