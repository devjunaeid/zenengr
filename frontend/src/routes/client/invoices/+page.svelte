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
				{data.invoices.total}
				{data.invoices.total === 1 ? 'invoice' : 'invoices'} available
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
				class="block w-full rounded-lg border-slate-300 py-1.5 pr-8 pl-3 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 sm:w-auto"
			>
				<option value="">All Statuses</option>
				{#each statusOptions.filter(Boolean) as opt (opt)}
					<option value={opt}>{humanize(opt)}</option>
				{/each}
			</select>
		</form>
	</div>

	{#if pdfErr}
		<div
			role="alert"
			class="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 shadow-2xs"
		>
			{pdfErr}
		</div>
	{/if}

	<!-- Invoices Table -->
	<div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		{#if data.invoices.items.length === 0}
			{#if hasFilter}
				<p class="px-6 py-8 text-center text-xs text-slate-500">No invoices match your filter.</p>
			{:else}
				<EmptyState
					title="No invoices yet"
					description="Invoices will appear here once they are issued for your projects."
				/>
			{/if}
		{:else}
		<!-- Mobile & Tablet cards (< lg): responsive grid -->
		<div class="grid grid-cols-1 gap-3.5 p-3 bg-slate-50/60 sm:grid-cols-2 lg:hidden">
			{#each data.invoices.items as inv (inv.id)}
				<div class="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 transition-shadow hover:shadow-xs">
					<div class="space-y-3">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<a
									href={resolve('/client/invoices/[id]', { id: inv.id })}
									class="flex items-center gap-1.5 text-sm font-bold text-indigo-600 transition-colors hover:text-indigo-800"
								>
									<Icon icon={fileDocumentOutline} class="h-4 w-4 shrink-0 text-slate-400" />
									{inv.invoice_number ?? 'Draft Invoice'}
								</a>
								<p class="mt-0.5 text-xs text-slate-600">
									{inv.project_name || 'General Project'}
								</p>
							</div>
							<StatusBadge status={inv.status} />
						</div>

						<div class="flex items-center justify-between rounded-lg bg-slate-50 p-2.5">
							<span class="text-xs text-slate-500">Amount Due</span>
							<span class="text-sm font-bold text-slate-900">{fmtPrice(inv.total)}</span>
						</div>

						{#if inv.due_date}
							<div class="text-xs text-slate-500">
								<span>Due date:</span>
								<span class="ml-1 font-medium text-slate-700">{formatDate(inv.due_date)}</span>
							</div>
						{/if}
					</div>

					<div class="flex items-center gap-2 pt-1">
						<a
							href={resolve('/client/invoices/[id]', { id: inv.id })}
							class="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
						>
							<Icon icon={printerOutline} class="h-3.5 w-3.5 text-slate-500" />
							View / Print
						</a>
						<button
							type="button"
							onclick={() => downloadPdf(inv)}
							disabled={downloadingId === inv.id}
							class="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-50 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
						>
							{#if downloadingId === inv.id}
								<Spinner class="h-3.5 w-3.5 text-indigo-600" />
							{:else}
								<Icon icon={downloadOutline} class="h-3.5 w-3.5 text-indigo-600" />
							{/if}
							Download PDF
						</button>
					</div>
				</div>
			{/each}
		</div>

		<!-- Desktop table (>= lg) -->
		<div class="relative hidden overflow-x-auto lg:block">
			<table class="min-w-full divide-y divide-slate-200 text-xs">
				<thead class="bg-slate-50/80">
					<tr>
						<th
							scope="col"
							class="px-3 py-3 text-left font-bold tracking-wider text-slate-600 uppercase sm:px-4"
						>
							Invoice Number
						</th>
						<th
							scope="col"
							class="px-3 py-3 text-left font-bold tracking-wider text-slate-600 uppercase sm:px-4"
						>
							Project
						</th>
						<th
							scope="col"
							class="px-3 py-3 text-left font-bold tracking-wider text-slate-600 uppercase sm:px-4"
						>
							Status
						</th>
						<th
							scope="col"
							class="px-3 py-3 text-right font-bold tracking-wider text-slate-600 uppercase sm:px-4"
						>
							Total
						</th>
						<th
							scope="col"
							class="px-3 py-3 text-left font-bold tracking-wider text-slate-600 uppercase sm:px-4"
						>
							Due Date
						</th>
						<th
							scope="col"
							class="px-3 py-3 text-right font-bold tracking-wider text-slate-600 uppercase sm:px-4"
						>
							Actions
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-100">
					{#each data.invoices.items as inv (inv.id)}
						<tr class="transition-colors hover:bg-slate-50/70">
							<td class="px-3 py-3.5 font-bold text-slate-900 sm:px-4">
								<a
									href={resolve('/client/invoices/[id]', { id: inv.id })}
									class="flex items-center gap-1.5 text-indigo-600 transition-colors hover:text-indigo-800"
								>
									<Icon icon={fileDocumentOutline} class="h-4 w-4 shrink-0 text-slate-400" />
									{inv.invoice_number ?? 'Draft'}
								</a>
							</td>
							<td class="px-3 py-3.5 font-medium text-slate-700 sm:px-4">
								{inv.project_name || '—'}
							</td>
							<td class="px-3 py-3.5 sm:px-4">
								<StatusBadge status={inv.status} />
							</td>
							<td
								class="px-3 py-3.5 text-right font-bold whitespace-nowrap text-slate-900 sm:px-4"
							>
								{fmtPrice(inv.total)}
							</td>
							<td class="px-3 py-3.5 whitespace-nowrap text-slate-600 sm:px-4">
								{formatDate(inv.due_date)}
							</td>
							<td class="px-3 py-3.5 text-right whitespace-nowrap sm:px-4">
								<div class="inline-flex items-center gap-1.5">
									<a
										href={resolve('/client/invoices/[id]', { id: inv.id })}
										class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50"
									>
										<Icon icon={printerOutline} class="h-3.5 w-3.5 text-slate-500" />
										View / Print
									</a>
									<button
										type="button"
										onclick={() => downloadPdf(inv)}
										disabled={downloadingId === inv.id}
										class="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-50"
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
