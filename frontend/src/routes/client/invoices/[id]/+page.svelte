<script>
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { formatDate, formatDateTime, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (portalAuth.token);

	/** @type {string|null} */
	let pdfErr = $state(null);
	let downloading = $state(false);
	let viewing = $state(false);

	const number = $derived(data.invoice.invoice_number ?? 'Draft');

	/**
	 * @param {string} lineItemId
	 */
	function descriptionOf(lineItemId) {
		return data.invoice.line_items.find((li) => li.id === lineItemId)?.description ?? 'Line item';
	}

	async function downloadPdf() {
		if (downloading) return;
		downloading = true;
		pdfErr = null;
		try {
			const filename = `${data.invoice.invoice_number ?? 'invoice'}.pdf`;
			await portalApi.downloadClientInvoicePdf(fetch, token, data.invoice.id, filename);
		} catch (e) {
			pdfErr = e instanceof ApiError ? e.message : 'Could not download the invoice PDF.';
		} finally {
			downloading = false;
		}
	}

	async function viewPdf() {
		if (viewing) return;
		viewing = true;
		pdfErr = null;
		try {
			const filename = `${data.invoice.invoice_number ?? 'invoice'}.pdf`;
			await portalApi.viewClientInvoicePdf(fetch, token, data.invoice.id, filename);
		} catch (e) {
			pdfErr = e instanceof ApiError ? e.message : 'Could not open the invoice PDF.';
		} finally {
			viewing = false;
		}
	}
</script>

<svelte:head><title>{number} — Client Portal</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/client/invoices')} class="hover:text-indigo-600">Invoices</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">{number}</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div class="flex items-center gap-3">
		<h1 class="text-2xl font-semibold text-slate-900">{number}</h1>
		<StatusBadge status={data.invoice.status} />
	</div>
	<div class="flex flex-wrap items-center gap-2">
		<button
			type="button"
			onclick={downloadPdf}
			disabled={downloading || viewing}
			aria-busy={downloading}
			class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if downloading}
				<Spinner class="h-4 w-4 text-indigo-600" />
			{:else}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path
						d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z"
					/>
					<path
						d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z"
					/>
				</svg>
			{/if}
			Download PDF
		</button>
		<button
			type="button"
			onclick={viewPdf}
			disabled={downloading || viewing}
			aria-busy={viewing}
			class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if viewing}
				<Spinner class="h-4 w-4 text-indigo-600" />
			{:else}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
					<path
						fill-rule="evenodd"
						d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
						clip-rule="evenodd"
					/>
				</svg>
			{/if}
			View
		</button>
	</div>
</div>

{#if pdfErr}
	<p
		role="alert"
		class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{pdfErr}
	</p>
{/if}

<div class="mt-6 grid gap-6 lg:grid-cols-2">
	<section
		class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="totals-h"
	>
		<h2 id="totals-h" class="text-base font-semibold text-slate-900">Totals</h2>
		<dl class="mt-4 grid gap-4 sm:grid-cols-3">
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Subtotal</dt>
				<dd class="mt-1 text-sm text-slate-900">{fmtPrice(data.invoice.subtotal)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Tax</dt>
				<dd class="mt-1 text-sm text-slate-900">{fmtPrice(data.invoice.tax_total)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total</dt>
				<dd class="mt-1 text-sm font-semibold text-slate-900">{fmtPrice(data.invoice.total)}</dd>
			</div>
		</dl>
	</section>

	<section
		class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="dates-h"
	>
		<h2 id="dates-h" class="text-base font-semibold text-slate-900">Dates</h2>
		<dl class="mt-4 grid gap-4 sm:grid-cols-2">
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Issue date</dt>
				<dd class="mt-1 text-sm text-slate-900">{formatDate(data.invoice.issue_date)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Due date</dt>
				<dd class="mt-1 text-sm text-slate-900">{formatDate(data.invoice.due_date)}</dd>
			</div>
			<div class="sm:col-span-2">
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Project</dt>
				<dd class="mt-1 text-sm">
					<a
						href={resolve('/client/projects/[id]', { id: data.invoice.project_id })}
						class="text-indigo-600 hover:text-indigo-500"
					>
						{data.invoice.project_name}
					</a>
				</dd>
			</div>
		</dl>
	</section>
</div>

<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="payment-status-h"
>
	<h2 id="payment-status-h" class="text-base font-semibold text-slate-900">Payment status</h2>
	<dl class="mt-4 grid gap-4 sm:grid-cols-2">
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Paid amount</dt>
			<dd class="mt-1 text-sm font-semibold text-green-700">
				{fmtPrice(data.invoice.paid_amount)}
			</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Balance due</dt>
			<dd class="mt-1 text-sm font-semibold text-slate-900">
				{fmtPrice(data.invoice.balance_due)}
			</dd>
		</div>
	</dl>
</section>

{#if data.invoice.notes}
	<section
		class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="notes-h"
	>
		<h2 id="notes-h" class="text-base font-semibold text-slate-900">Notes</h2>
		<p class="mt-2 text-sm whitespace-pre-wrap text-slate-700">{data.invoice.notes}</p>
	</section>
{/if}

<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="items-h"
>
	<div class="border-b border-slate-200 px-6 py-4">
		<h2 id="items-h" class="text-base font-semibold text-slate-900">Line items</h2>
		<p class="mt-0.5 text-sm text-slate-500">
			{data.invoice.line_items.length}
			{data.invoice.line_items.length === 1 ? 'item' : 'items'}
		</p>
	</div>
	{#if data.invoice.line_items.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No line items on this invoice.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Description</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Qty</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Unit price</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Amount</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.invoice.line_items as li (li.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">{li.description}</td>
							<td class="px-4 py-3 text-right text-sm text-slate-700">{li.quantity}</td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(li.unit_price)}</td
							>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-900"
								>{fmtPrice(li.amount)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="transactions-h"
>
	<div class="border-b border-slate-200 px-6 py-4">
		<h2 id="transactions-h" class="text-base font-semibold text-slate-900">Payment history</h2>
		<p class="mt-0.5 text-sm text-slate-500">
			{data.transactions.length}
			{data.transactions.length === 1 ? 'payment' : 'payments'} recorded
		</p>
	</div>
	{#if data.transactions.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No payments yet.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Type</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Amount</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Method</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Reference</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Date</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.transactions as t (t.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3">
								{#if t.direction === 'credit'}
									<span
										class="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 ring-1 ring-red-600/20 ring-inset"
									>
										Refund
									</span>
								{:else}
									<span
										class="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 ring-1 ring-green-600/20 ring-inset"
									>
										Payment
									</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-sm font-medium whitespace-nowrap text-slate-900"
								>{t.direction === 'credit' ? `−${fmtPrice(t.amount)}` : fmtPrice(t.amount)}</td
							>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-700"
								>{humanize(t.method)}</td
							>
							<td class="px-4 py-3 text-sm text-slate-700">{t.reference_note || '—'}</td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{formatDateTime(t.recorded_at)}</td
							>
						</tr>
						{#if t.allocations.length > 0}
							<tr class="bg-slate-50/50">
								<td colspan="5" class="px-4 py-2">
									<details class="group">
										<summary
											class="flex cursor-pointer list-none items-center gap-1 text-xs text-slate-500 hover:text-indigo-600 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="h-3.5 w-3.5 transition-transform group-open:rotate-90"
												aria-hidden="true"
											>
												<path
													fill-rule="evenodd"
													d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
													clip-rule="evenodd"
												/>
											</svg>
											Allocated to {t.allocations.length}
											{t.allocations.length === 1 ? 'item' : 'items'}
										</summary>
										<ul
											class="mt-2 space-y-1 rounded-md border border-slate-200 bg-white p-3 text-sm"
										>
											{#each t.allocations as a (a.id)}
												<li class="flex items-center justify-between gap-3">
													<span class="text-slate-700">{descriptionOf(a.line_item_id)}</span>
													<span class="whitespace-nowrap text-slate-900">{fmtPrice(a.amount)}</span>
												</li>
											{/each}
										</ul>
									</details>
								</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>
