<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	let canManage = $derived(auth.can('manage', 'projects'));
	let hasFilter = $derived(
		Boolean(untrack(() => data.filters.q)) || Boolean(untrack(() => data.filters.status))
	);

	let q = $state(untrack(() => data.filters.q));
	let status = $state(untrack(() => data.filters.status));

	const statusOptions = ['', 'draft', 'active', 'on_hold', 'completed', 'cancelled'];

	/**
	 * @param {number} p
	 */
	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (q) params.set('q', q);
		if (status) params.set('status', status);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/app/projects')}?${qs}` : resolve('/app/projects');
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

	/**
	 * @param {{ milestone_total: number, milestone_completed: number }} p
	 */
	function progressPct(p) {
		if (!p.milestone_total) return 0;
		return Math.min(100, Math.round((p.milestone_completed / p.milestone_total) * 100));
	}
</script>

<svelte:head><title>Projects — ZenEngr</title></svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Projects</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.projects.total}
			{data.projects.total === 1 ? 'project' : 'projects'}
		</p>
	</div>
	{#if canManage}
		<a
			href={resolve('/app/projects/new')}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			New project
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
			placeholder="Project name"
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
			{#each statusOptions as opt (opt)}
				<option value={opt}>{opt === '' ? 'All' : humanize(opt)}</option>
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
	{#if data.projects.items.length === 0}
		{#if hasFilter}
			<p class="px-6 py-8 text-sm text-slate-500">
				No results match your search. Try different filters.
			</p>
		{:else}
			<EmptyState
				title="No projects yet"
				description="Create your first project to start tracking work for a client."
			>
				{#if canManage}
					<a
						href={resolve('/app/projects/new')}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						New project
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
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Services</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Progress</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Start</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Created</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.projects.items as p (p.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/projects/[id]', { id: p.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{p.name}
								</a>
							</td>
							<td class="px-4 py-3"><StatusBadge status={p.status} /></td>
							<td class="px-4 py-3 text-right text-sm text-slate-700">{p.service_count}</td>
							<td class="px-4 py-3 text-sm text-slate-700">
								{#if p.milestone_total > 0}
									<div class="flex items-center gap-2">
										<div
											class="h-1.5 w-24 rounded-full bg-slate-100"
											role="progressbar"
											aria-valuenow={p.milestone_completed}
											aria-valuemin={0}
											aria-valuemax={p.milestone_total}
											aria-label={`Milestone progress for ${p.name}`}
										>
											<div
												class="h-1.5 rounded-full bg-indigo-600"
												style="width: {progressPct(p)}%"
											></div>
										</div>
										<span class="text-xs whitespace-nowrap text-slate-600"
											>{p.milestone_completed}/{p.milestone_total}</span
										>
									</div>
								{:else}
									<span class="text-xs text-slate-400">No milestones</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(p.start_date)}</td
							>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(p.created_at)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Pagination
			page={data.projects.page}
			pageSize={data.projects.page_size}
			total={data.projects.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
