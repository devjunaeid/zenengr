<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { formatDate, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	let hasFilter = $derived(
		Boolean(untrack(() => data.filters.status)) || Boolean(untrack(() => data.filters.project_id))
	);

	let status = $state(untrack(() => data.filters.status));
	let projectId = $state(untrack(() => data.filters.project_id));

	const statusOptions = ['', 'draft', 'issued', 'partially_paid', 'paid', 'void'];

	/**
	 * @param {number} p
	 */
	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (status) params.set('status', status);
		if (projectId) params.set('project_id', projectId);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/app/invoices')}?${qs}` : resolve('/app/invoices');
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
</script>

<svelte:head><title>Invoices — ZenEngr</title></svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Invoices</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.invoices.total}
			{data.invoices.total === 1 ? 'invoice' : 'invoices'}
		</p>
	</div>
	<a
		href={resolve('/app/invoices/new')}
		class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		New invoice
	</a>
</div>

<form
	class="mt-6 flex flex-wrap items-end gap-3"
	onsubmit={(e) => {
		e.preventDefault();
		applyFilters();
	}}
>
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
	<div>
		<label for="f-project" class="block text-xs font-medium text-slate-600">Project</label>
		<select
			id="f-project"
			bind:value={projectId}
			class="mt-1 block w-64 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		>
			<option value="">All projects</option>
			{#each data.projects as p (p.id)}
				<option value={p.id}>{p.name}</option>
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
	{#if data.invoices.items.length === 0}
		{#if hasFilter}
			<p class="px-6 py-8 text-sm text-slate-500">
				No results match your filters. Try different filters.
			</p>
		{:else}
			<EmptyState
				title="No invoices yet"
				description="Create an invoice to bill a project for its services."
			>
				<a
					href={resolve('/app/invoices/new')}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					New invoice
				</a>
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
							>Invoice number</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Project</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Total</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Issued</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Created</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.invoices.items as inv (inv.id)}
						{@const projectName = data.projects.find((p) => p.id === inv.project_id)?.name}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/invoices/[id]', { id: inv.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{inv.invoice_number ?? '—'}
								</a>
							</td>
							<td class="px-4 py-3 text-sm text-slate-700">
								{#if inv.project_id}
									{projectName ?? '—'}
								{:else}
									<span
										class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-500/20 ring-inset"
									>
										Internal
									</span>
								{/if}
							</td>
							<td class="px-4 py-3">
								<span class="flex flex-wrap items-center gap-2">
									<StatusBadge status={inv.status} />
									{#if inv.is_auto}
										<span
											title="Statement invoice — internal, project-scoped"
											class="inline-flex items-center rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800 ring-1 ring-violet-600/20 ring-inset"
										>
											Statement
										</span>
									{/if}
								</span>
							</td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(inv.total)}</td
							>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(inv.issue_date)}</td
							>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(inv.created_at)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Pagination
			page={data.invoices.page}
			pageSize={data.invoices.page_size}
			total={data.invoices.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
