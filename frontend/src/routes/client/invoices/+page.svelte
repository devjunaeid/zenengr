<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LedgerTable from '$lib/components/LedgerTable.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { formatDate, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	let hasFilter = $derived(Boolean(untrack(() => data.filters.status)));

	let status = $state(untrack(() => data.filters.status));

	const statusOptions = ['', 'draft', 'issued', 'partially_paid', 'paid'];

	/**
	 * @param {number} p
	 */
	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (status) params.set('status', status);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/client/invoices')}?${qs}` : resolve('/client/invoices');
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

<svelte:head><title>Invoices — Client Portal</title></svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Invoices</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.invoices.total}
			{data.invoices.total === 1 ? 'invoice' : 'invoices'}
		</p>
	</div>
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
	<button
		type="submit"
		class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		Apply
	</button>
</form>

{#if data.ledger}
	<section
		class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
		aria-labelledby="balance-h"
	>
		<div
			class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4"
		>
			<h2 id="balance-h" class="text-base font-semibold text-slate-900">Your balance</h2>
			<p class="text-sm text-slate-600">
				Advance balance:
				<span
					class="font-semibold {Number(data.ledger.advance_balance) > 0
						? 'text-green-600'
						: 'text-slate-900'}"
				>
					{fmtPrice(data.ledger.advance_balance)}
				</span>
			</p>
		</div>
		<LedgerTable entries={data.ledger.entries} emptyMessage="No ledger entries yet." />
	</section>
{/if}

<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	{#if data.invoices.items.length === 0}
		{#if hasFilter}
			<p class="px-6 py-8 text-sm text-slate-500">
				No results match your filters. Try different filters.
			</p>
		{:else}
			<EmptyState
				title="No invoices yet"
				description="Invoices will appear here once they are issued for your projects."
			/>
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
							>Due date</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.invoices.items as inv (inv.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/client/invoices/[id]', { id: inv.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{inv.invoice_number ?? '—'}
								</a>
							</td>
							<td class="px-4 py-3 text-sm text-slate-700">{inv.project_name}</td>
							<td class="px-4 py-3"><StatusBadge status={inv.status} /></td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(inv.total)}</td
							>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(inv.due_date)}</td
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
