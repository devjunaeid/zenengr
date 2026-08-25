<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, fmtPrice } from '$lib/utils/format.js';

	let { data } = $props();

	let canManage = $derived(auth.can('manage', 'services'));
	let hasFilter = $derived(
		Boolean(untrack(() => data.filters.q)) || Boolean(untrack(() => data.filters.is_active))
	);

	let q = $state(untrack(() => data.filters.q));
	let isActive = $state(untrack(() => data.filters.is_active));

	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (q) params.set('q', q);
		if (isActive) params.set('is_active', isActive);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/app/settings/services')}?${qs}` : resolve('/app/settings/services');
	}

	function applyFilters() {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(1));
	}

	function gotoPage(p) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(p));
	}
</script>

<svelte:head><title>Services — ZenEngr</title></svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Services</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.services.total}
			{data.services.total === 1 ? 'service' : 'services'}
		</p>
	</div>
	{#if canManage}
		<a
			href={resolve('/app/settings/services/new')}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			New service
		</a>
	{/if}
</div>

<form
	class="mt-6 flex flex-wrap items-end gap-3"
	onsubmit={(e) => {
		e.preventDefault();
		applyFilters();
	}}
>
	<div>
		<label for="f-q" class="block text-xs font-medium text-slate-600">Search</label>
		<input
			id="f-q"
			type="search"
			bind:value={q}
			placeholder="Name or description"
			class="mt-1 block w-64 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>
	<div>
		<label for="f-status" class="block text-xs font-medium text-slate-600">Status</label>
		<select
			id="f-status"
			bind:value={isActive}
			class="mt-1 block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		>
			<option value="">All</option>
			<option value="active">Active</option>
			<option value="inactive">Inactive</option>
		</select>
	</div>
	<button
		type="submit"
		class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		Apply
	</button>
</form>

<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	{#if data.services.items.length === 0}
		{#if hasFilter}
			<p class="px-6 py-8 text-sm text-slate-500">
				No results match your search. Try different filters.
			</p>
		{:else}
			<EmptyState
				title="No services yet"
				description="Create your first service to use as a template for projects."
			>
				{#if canManage}
					<a
						href={resolve('/app/settings/services/new')}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						New service
					</a>
				{/if}
			</EmptyState>
		{/if}
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Name</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Description</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Default price</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Steps</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Created</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.services.items as s (s.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/settings/services/[id]', { id: s.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{s.name}
								</a>
							</td>
							<td class="max-w-xs px-4 py-3 text-sm text-slate-600">
								{#if s.description}
									<span class="line-clamp-2">{s.description}</span>
								{:else}
									<span class="text-slate-400">—</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(s.default_price)}</td
							>
							<td class="px-4 py-3 text-right text-sm text-slate-700">{s.step_count}</td>
							<td class="px-4 py-3">
								<StatusBadge status={s.is_active ? 'active' : 'inactive'} />
							</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(s.created_at)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Pagination
			page={data.services.page}
			pageSize={data.services.page_size}
			total={data.services.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
