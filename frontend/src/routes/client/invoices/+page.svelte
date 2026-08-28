<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Icon from '@iconify/svelte';
	import printerOutline from '@iconify-icons/mdi/printer-outline';
	import downloadOutline from '@iconify-icons/mdi/download-outline';
	import fileDocumentOutline from '@iconify-icons/mdi/file-document-outline';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { ApiError } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { formatDate, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (portalAuth.token);

	let hasFilter = $derived(Boolean(untrack(() => data.filters.status)));
	let status = $state(untrack(() => data.filters.status));
	let downloadingId = $state(/** @type {string|null} */ (null));
	let pdfErr = $state(/** @type {string|null} */ (null));

	const statusOptions = ['', 'issued', 'partially_paid', 'paid'];

	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (status) params.set('status', status);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/client/invoices')}?${qs}` : resolve('/client/invoices');
	}

	function applyFilters() {
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(buildUrl(1));
	}

	function gotoPage(p) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(buildUrl(p));
	}

	async function downloadPdf(inv) {
		if (downloadingId) return;
		downloadingId = inv.id;
		pdfErr = null;
		try {
			const filename = `${inv.invoice_number ?? 'invoice'}.pdf`;
			await portalApi.downloadClientInvoicePdf(fetch, token, inv.id, filename);
		} catch (e) {
			pdfErr = e instanceof ApiError ? e.message : 'Could not download the invoice PDF.';
		} finally {
			downloadingId = null;
		}
	}
</script>

<svelte:head><title>Invoices — Client Portal</title></svelte:head>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-xl font-bold text-slate-900">Invoices</h1>
			<p class="mt-0.5 text-xs text-slate-500">
				{data.invoices.total} {data.invoices.total === 1 ? 'invoice' : 'invoices'} available
			</p>
		</div>

		<!-- Status Filter -->
		<form
			class="flex items-center gap-2"
			onsubmit={(e) => {
				e.preventDefault();
				applyFilters();
			}}
		>
			<select
				id="f-status"
				bind:value={status}
				onchange={applyFilters}
				class="block rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 py-1.5 pl-3 pr-8"
			>
				<option value="">All Statuses</option>
				{#each statusOptions.filter(Boolean) as opt (opt)}
					<option value={opt}>{humanize(opt)}</option>
				{/each}
			</select>
		</form>
	</div>

	{#if pdfErr}
		<div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 shadow-2xs">
			{pdfErr}
		</div>
	{/if}

	<!-- Invoices Table -->
	<div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		{#if data.invoices.items.length === 0}
			{#if hasFilter}
				<p class="px-6 py-8 text-center text-xs text-slate-500">
					No invoices match your filter.
				</p>
			{:else}
				<EmptyState
					title="No invoices yet"
					description="Invoices will appear here once they are issued for your projects."
				/>
			{/if}
		{:else}
			<div class="overflow-x-auto">
				<table class="min-w-full divide-y divide-slate-200 text-xs">
					<thead class="bg-slate-50/80">
						<tr>
							<th scope="col" class="px-4 py-3 text-left font-bold uppercase tracking-wider text-slate-600">
								Invoice Number
							</th>
							<th scope="col" class="px-4 py-3 text-left font-bold uppercase tracking-wider text-slate-600">
								Project
							</th>
							<th scope="col" class="px-4 py-3 text-left font-bold uppercase tracking-wider text-slate-600">
								Status
							</th>
							<th scope="col" class="px-4 py-3 text-right font-bold uppercase tracking-wider text-slate-600">
								Total
							</th>
							<th scope="col" class="px-4 py-3 text-left font-bold uppercase tracking-wider text-slate-600">
								Due Date
							</th>
							<th scope="col" class="px-4 py-3 text-right font-bold uppercase tracking-wider text-slate-600">
								Actions
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-100">
						{#each data.invoices.items as inv (inv.id)}
							<tr class="hover:bg-slate-50/70 transition-colors">
								<td class="px-4 py-3.5 font-bold text-slate-900">
									<a
										href={resolve('/client/invoices/[id]', { id: inv.id })}
										class="text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1.5"
									>
										<Icon icon={fileDocumentOutline} class="h-4 w-4 text-slate-400" />
										{inv.invoice_number ?? 'Draft'}
									</a>
								</td>
								<td class="px-4 py-3.5 text-slate-700 font-medium">
									{inv.project_name || '—'}
								</td>
								<td class="px-4 py-3.5">
									<StatusBadge status={inv.status} />
								</td>
								<td class="px-4 py-3.5 text-right font-bold text-slate-900 whitespace-nowrap">
									{fmtPrice(inv.total)}
								</td>
								<td class="px-4 py-3.5 text-slate-600 whitespace-nowrap">
									{formatDate(inv.due_date)}
								</td>
								<td class="px-4 py-3.5 text-right whitespace-nowrap">
									<div class="inline-flex items-center gap-1.5">
										<a
											href={resolve('/client/invoices/[id]', { id: inv.id })}
											class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
										>
											<Icon icon={printerOutline} class="h-3.5 w-3.5 text-slate-500" />
											View / Print
										</a>
										<button
											type="button"
											onclick={() => downloadPdf(inv)}
											disabled={downloadingId === inv.id}
											class="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors disabled:opacity-50"
										>
											{#if downloadingId === inv.id}
												<Spinner class="h-3.5 w-3.5 text-indigo-600" />
											{:else}
												<Icon icon={downloadOutline} class="h-3.5 w-3.5 text-indigo-600" />
											{/if}
											PDF
										</button>
									</div>
								</td>
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
</div>
