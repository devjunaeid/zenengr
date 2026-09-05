<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { formatDate } from '$lib/utils/format.js';

	import { untrack } from 'svelte';

	let { data } = $props();

	let q = $state(untrack(() => data.filters.q));
	let status = $state(untrack(() => data.filters.status));
	let sort = $state(untrack(() => data.filters.sort));

	const statuses = ['trial', 'active', 'suspended', 'cancelled'];

	/**
	 * @param {number} page
	 * @param {string} [sortValue]
	 */
	function gotoPage(page, sortValue = sort) {
		const url = `${resolve('/admin/tenants')}?q=${encodeURIComponent(q)}&status=${status}&sort=${encodeURIComponent(sortValue)}&page=${page}`;
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(url);
	}

	function applyFilters() {
		gotoPage(1);
	}

	/**
	 * @param {'business_name'|'created_at'} field
	 */
	function toggleSort(field) {
		let next;
		if (sort === field) next = `-${field}`;
		else if (sort === `-${field}`) next = '';
		else next = field;
		gotoPage(1, next);
	}

	/**
	 * @param {'business_name'|'created_at'} field
	 */
	function sortIndicator(field) {
		if (sort === field) return '▲';
		if (sort === `-${field}`) return '▼';
		return '';
	}
</script>

<svelte:head><title>Tenants — Super Admin</title></svelte:head>

<div class="flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Tenants</h1>
		<p class="mt-1 text-sm text-slate-500">{data.tenants.total} total</p>
	</div>
	<a
		href={resolve('/admin/tenants/new')}
		class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		New tenant
	</a>
</div>

<form
	class="mt-6 flex flex-wrap items-end gap-3"
	onsubmit={(e) => {
		e.preventDefault();
		applyFilters();
	}}
>
	<div class="min-w-0 flex-1">
		<label for="q" class="block text-xs font-medium text-slate-600">Search</label>
		<input
			id="q"
			type="search"
			bind:value={q}
			placeholder="Name or slug"
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:w-64"
		/>
	</div>
	<div>
		<label for="status" class="block text-xs font-medium text-slate-600">Status</label>
		<select
			id="status"
			bind:value={status}
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:w-auto"
		>
			<option value="">All statuses</option>
			{#each statuses as s (s)}
				<option value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
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
	{#if data.tenants.items.length === 0}
		<EmptyState
			title="No tenants found"
			description="No results match your search. Try different filters."
		/>
	{:else}
		<!-- Mobile & Tablet cards (< lg): responsive grid -->
		<div class="grid grid-cols-1 gap-3.5 p-3 bg-slate-50/60 sm:grid-cols-2 lg:hidden">
			{#each data.tenants.items as tenant (tenant.id)}
				<div class="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 transition-shadow hover:shadow-xs">
					<div class="space-y-3">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<a
									href={resolve('/admin/tenants/[id]', { id: tenant.id })}
									class="text-sm font-semibold text-indigo-600 hover:text-indigo-500"
								>
									{tenant.business_name}
								</a>
								<p class="mt-0.5 font-mono text-xs text-slate-500">{tenant.slug}</p>
							</div>
							<StatusBadge status={tenant.status} />
						</div>

						<div class="grid grid-cols-2 gap-2 rounded-lg bg-slate-50 p-2.5 text-xs">
							<div>
								<span class="text-slate-400">Plan:</span>
								<span class="ml-1 font-medium text-slate-700">{tenant.plan_name}</span>
							</div>
							<div>
								<span class="text-slate-400">Users:</span>
								<span class="ml-1 font-medium text-slate-700">{tenant.active_user_count}</span>
							</div>
							<div class="col-span-2">
								<span class="text-slate-400">Created:</span>
								<span class="ml-1 text-slate-600">{formatDate(tenant.created_at)}</span>
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-1">
						<a
							href={resolve('/admin/tenants/[id]', { id: tenant.id })}
							class="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
						>
							Manage tenant
						</a>
					</div>
				</div>
			{/each}
		</div>

		<!-- Desktop table (>= lg) -->
		<div class="relative hidden overflow-x-auto lg:block">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th scope="col" class="px-3 py-3 text-left sm:px-4">
							<button
								type="button"
								onclick={() => toggleSort('business_name')}
								class="inline-flex items-center gap-1 text-xs font-semibold tracking-wide text-slate-600 uppercase hover:text-indigo-600"
							>
								Name
								<span class="text-slate-400">{sortIndicator('business_name')}</span>
							</button>
						</th>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Slug</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Plan</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Users</th
						>
						<th scope="col" class="px-3 py-3 text-left sm:px-4">
							<button
								type="button"
								onclick={() => toggleSort('created_at')}
								class="inline-flex items-center gap-1 text-xs font-semibold tracking-wide text-slate-600 uppercase hover:text-indigo-600"
							>
								Created
								<span class="text-slate-400">{sortIndicator('created_at')}</span>
							</button>
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.tenants.items as tenant (tenant.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-3 py-3 text-sm font-medium sm:px-4">
								<a
									href={resolve('/admin/tenants/[id]', { id: tenant.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{tenant.business_name}
								</a>
							</td>
							<td class="px-3 py-3 font-mono text-sm text-slate-600 sm:px-4">{tenant.slug}</td>
							<td class="px-3 py-3 sm:px-4"><StatusBadge status={tenant.status} /></td>
							<td class="px-3 py-3 text-sm text-slate-600 sm:px-4">{tenant.plan_name}</td>
							<td class="px-3 py-3 text-sm text-slate-600 sm:px-4">{tenant.active_user_count}</td>
							<td class="px-3 py-3 text-sm text-slate-600 sm:px-4"
								>{formatDate(tenant.created_at)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Pagination
			page={data.tenants.page}
			pageSize={data.tenants.page_size}
			total={data.tenants.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
