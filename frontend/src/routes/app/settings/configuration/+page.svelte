<script>
	import { untrack } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { ApiError } from '$lib/api/client.js';
	import * as tenantApi from '$lib/api/tenant.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	let isAdmin = $derived(auth.isTenantAdmin);

	// ---- Settings table ----
	// Draft values keyed by setting key; masked (null) values start empty.
	/** @type {Record<string, string>} */
	let drafts = $state(
		untrack(() => Object.fromEntries(data.settings.map((s) => [s.key, s.value ?? ''])))
	);
	/** @type {string|null} */
	let savingKey = $state(null);
	/** @type {Record<string, string>} */
	let savedKeys = $state({});
	/** @type {string|null} */
	let settingsErr = $state(null);

	/** @param {string} key */
	async function saveSetting(key) {
		settingsErr = null;
		savingKey = key;
		try {
			await tenantApi.updateSetting(fetch, token, key, drafts[key]);
			savedKeys = { ...savedKeys, [key]: 'Saved.' };
			setTimeout(() => {
				const next = { ...savedKeys };
				delete next[key];
				savedKeys = next;
			}, 3000);
			await invalidateAll();
		} catch (e) {
			settingsErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			savingKey = null;
		}
	}
</script>

<svelte:head><title>Configuration — ZenEngr</title></svelte:head>

<h1 class="text-2xl font-semibold text-slate-900">Configuration</h1>

<!-- Tenant settings -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="settings-h"
>
	<h2
		id="settings-h"
		class="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
	>
		Configuration
	</h2>
	{#if settingsErr}
		<p
			role="alert"
			class="mx-6 mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{settingsErr}
		</p>
	{/if}
	{#if data.settings.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">
			No configurable settings defined for this tenant yet.
		</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Key</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Permission</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Value</th
						>
						<th scope="col" class="px-4 py-3"><span class="sr-only">Actions</span></th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.settings as s (s.key)}
						<tr>
							<td class="px-4 py-3 font-mono text-sm text-slate-800">{s.key}</td>
							<td class="px-4 py-3 text-sm text-slate-600">{s.permission_level}</td>
							<td class="px-4 py-3">
								{#if s.editable && isAdmin}
									<label for="set-{s.key}" class="sr-only">Value for {s.key}</label>
									<input
										id="set-{s.key}"
										type="text"
										bind:value={drafts[s.key]}
										placeholder={s.value === null ? '••••••' : ''}
										class="block w-64 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
									/>
								{:else}
									<span class="text-sm text-slate-600">{s.value ?? '••••••'}</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-right">
								{#if s.editable && isAdmin}
									<button
										type="button"
										disabled={savingKey === s.key}
										aria-busy={savingKey === s.key}
										onclick={() => saveSetting(s.key)}
										class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
									>
										{#if savingKey === s.key}<Spinner class="h-3.5 w-3.5" />{/if}
										Save
									</button>
									{#if savedKeys[s.key]}
										<span role="status" class="ml-2 text-xs text-green-700">{savedKeys[s.key]}</span
										>
									{/if}
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>
