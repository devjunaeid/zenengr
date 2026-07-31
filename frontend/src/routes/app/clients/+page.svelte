<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Pagination from '$lib/components/Pagination.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	let canManage = $derived(auth.user?.role === 'admin' || auth.user?.role === 'manager');
	let hasFilter = $derived(
		Boolean(untrack(() => data.filters.q)) ||
			Boolean(untrack(() => data.filters.status)) ||
			Boolean(untrack(() => data.filters.tag))
	);

	let q = $state(untrack(() => data.filters.q));
	let status = $state(untrack(() => data.filters.status));
	let tag = $state(untrack(() => data.filters.tag));

	/**
	 * Build a URL with the current filters and the given page number.
	 * @param {number} p
	 */
	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (q) params.set('q', q);
		if (status) params.set('status', status);
		if (tag) params.set('tag', tag);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/app/clients')}?${qs}` : resolve('/app/clients');
	}

	function applyFilters() {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(1));
	}

	/** @param {number} p */
	function gotoPage(p) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(p));
	}

	/** @param {string|number|null|undefined} n */
	function fmtNumber(n) {
		if (n == null || n === '') return '—';
		const num = typeof n === 'string' ? Number(n) : n;
		if (Number.isNaN(num)) return '—';
		return new Intl.NumberFormat(undefined).format(num);
	}
</script>

<svelte:head><title>Clients — ZenEngr</title></svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Clients</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.clients.total}
			{data.clients.total === 1 ? 'client' : 'clients'}
		</p>
	</div>
	{#if canManage}
		<a
			href={resolve('/app/clients/new')}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			New client
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
			placeholder="Name or email"
			class="mt-1 block w-64 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>
	<div>
		<label for="f-status" class="block text-xs font-medium text-slate-600">Status</label>
		<select
			id="f-status"
			bind:value={status}
			class="mt-1 block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		>
			<option value="">All</option>
			<option value="active">Active</option>
			<option value="archived">Archived</option>
		</select>
	</div>
	<div>
		<label for="f-tag" class="block text-xs font-medium text-slate-600">Tag</label>
		<select
			id="f-tag"
			bind:value={tag}
			class="mt-1 block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		>
			<option value="">All tags</option>
			{#each data.tags as t (t)}
				<option value={t}>{t}</option>
			{/each}
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
	{#if data.clients.items.length === 0}
		{#if hasFilter}
			<p class="px-6 py-8 text-sm text-slate-500">
				No results match your search. Try different filters.
			</p>
		{:else}
			<EmptyState title="No clients yet" description="Create your first client to get started.">
				{#if canManage}
					<a
						href={resolve('/app/clients/new')}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
					>
						New client
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
							>Email</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Active projects</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Total invoiced</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Outstanding</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Tags</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Created</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.clients.items as c (c.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/clients/[id]', { id: c.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{c.name}
								</a>
								<p class="mt-0.5 text-xs text-slate-500">{humanize(c.client_type)}</p>
							</td>
							<td class="px-4 py-3 text-sm text-slate-600">{c.email ?? '—'}</td>
							<td class="px-4 py-3"><StatusBadge status={c.status} /></td>
							<td class="px-4 py-3 text-right text-sm text-slate-700"
								>{fmtNumber(c.active_projects)}</td
							>
							<td class="px-4 py-3 text-right text-sm text-slate-700"
								>{fmtNumber(c.total_invoiced)}</td
							>
							<td class="px-4 py-3 text-right text-sm text-slate-700"
								>{fmtNumber(c.total_outstanding)}</td
							>
							<td class="px-4 py-3">
								<div class="flex flex-wrap gap-1">
									{#each c.tags as t (t)}
										<span
											class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-300 ring-inset"
										>
											{t}
										</span>
									{/each}
									{#if c.tags.length === 0}
										<span class="text-xs text-slate-400">—</span>
									{/if}
								</div>
							</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(c.created_at)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Pagination
			page={data.clients.page}
			pageSize={data.clients.page_size}
			total={data.clients.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
