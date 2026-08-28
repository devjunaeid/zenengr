<script>
	import Icon from '@iconify/svelte';
	import printerOutline from '@iconify-icons/mdi/printer-outline';
	import downloadOutline from '@iconify-icons/mdi/download-outline';
	import arrowLeft from '@iconify-icons/mdi/arrow-left';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { formatDate, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (portalAuth.token);
	const client = /** @type {import('$lib/api/portal.js').PortalClient} */ (portalAuth.client);

	let pdfErr = $state(/** @type {string|null} */ (null));
	let downloading = $state(false);

	const number = $derived(data.invoice.invoice_number ?? 'Draft Invoice');

	const invTotal = $derived(Number(data.invoice.total) || 0);
	const paidSum = $derived(
		data.transactions && data.transactions.length > 0
			? data.transactions.reduce((acc, tx) => acc + (tx.direction === 'debit' ? Number(tx.amount) : -Number(tx.amount)), 0)
			: Number(data.invoice.paid_amount) || 0
	);
	const balanceDue = $derived(Math.max(0, invTotal - paidSum));
	const advanceCredit = $derived(Math.max(0, paidSum - invTotal));

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

	function printInvoice() {
		window.print();
	}
</script>

<svelte:head>
	<title>{number} — {portalAuth.tenantName || 'Client Portal'}</title>
</svelte:head>

<div class="space-y-6 max-w-4xl mx-auto">
	<!-- Action Bar (Hidden in print) -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 print:hidden">
		<nav aria-label="Breadcrumb" class="text-xs font-semibold text-slate-500">
			<ol class="flex items-center gap-1.5">
				<li>
					<a href={resolve('/client/invoices')} class="hover:text-indigo-600 flex items-center gap-1">
						<Icon icon={arrowLeft} class="h-3.5 w-3.5" />
						Invoices
					</a>
				</li>
				<li aria-hidden="true" class="text-slate-300">/</li>
				<li class="font-bold text-slate-800">{number}</li>
			</ol>
		</nav>

		<div class="flex items-center gap-2">
			<button
				type="button"
				onclick={printInvoice}
				class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
			>
				<Icon icon={printerOutline} class="h-4 w-4 text-slate-500" />
				Print Invoice
			</button>
			<button
				type="button"
				onclick={downloadPdf}
				disabled={downloading}
				class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 transition-colors disabled:opacity-60"
			>
				{#if downloading}
					<Spinner class="h-4 w-4 text-white" />
				{:else}
					<Icon icon={downloadOutline} class="h-4 w-4" />
				{/if}
				Download PDF
			</button>
		</div>
	</div>

	{#if pdfErr}
		<div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 shadow-2xs print:hidden">
			{pdfErr}
		</div>
	{/if}

	<!-- Printable Visual Invoice Document -->
	<article id="printable-invoice" class="rounded-2xl border border-slate-200 bg-white p-8 sm:p-12 shadow-sm print:border-none print:shadow-none print:p-0 print:m-0">
		<!-- Header / Brand -->
		<div class="flex flex-col sm:flex-row justify-between items-start gap-6 border-b border-slate-200 pb-8">
			<div class="flex items-center gap-4">
				{#if data.invoice.tenant_logo_url}
					<img
						src={data.invoice.tenant_logo_url}
						alt={data.invoice.tenant_business_name || portalAuth.tenantName || 'Company Logo'}
						class="h-12 w-auto max-w-[180px] object-contain rounded"
					/>
				{/if}
				<div>
					<h2 class="text-2xl font-black text-slate-900 tracking-tight">
						{data.invoice.tenant_business_name || portalAuth.tenantName || 'INVOICE'}
					</h2>
					<p class="text-xs text-slate-500 mt-0.5">Official Client Statement</p>
				</div>
			</div>

			<div class="text-left sm:text-right">
				<div class="inline-flex items-center gap-2">
					<span class="text-base font-bold text-slate-900">{number}</span>
					<StatusBadge status={data.invoice.status} />
				</div>
				<p class="text-xs text-slate-500 mt-1">
					Project: <span class="font-semibold text-slate-800">{data.invoice.project_name || 'General Project'}</span>
				</p>
			</div>
		</div>

		<!-- Billing Info & Dates Grid -->
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-8 py-8 border-b border-slate-200 text-xs">
			<div>
				<h3 class="font-bold uppercase tracking-wider text-slate-400 text-[10px]">Billed To</h3>
				<p class="mt-2 text-sm font-bold text-slate-900">{client.name}</p>
				{#if client.email}
					<p class="text-slate-600 mt-0.5">{client.email}</p>
				{/if}
				{#if client.phone}
					<p class="text-slate-600 mt-0.5">{client.phone}</p>
				{/if}
				{#if client.tax_id}
					<p class="text-slate-600 mt-0.5">Tax ID / VAT: {client.tax_id}</p>
				{/if}
			</div>

			<div class="sm:text-right space-y-1.5">
				<div>
					<span class="text-slate-500">Issue Date:</span>
					<span class="font-semibold text-slate-900 ml-2">{formatDate(data.invoice.issue_date)}</span>
				</div>
				<div>
					<span class="text-slate-500">Due Date:</span>
					<span class="font-semibold text-slate-900 ml-2">{formatDate(data.invoice.due_date)}</span>
				</div>
				{#if data.invoice.project_id}
					<div>
						<span class="text-slate-500">Project Reference:</span>
						<a
							href={resolve('/client/projects/[id]', { id: data.invoice.project_id })}
							class="font-semibold text-indigo-600 hover:text-indigo-700 ml-2 print:text-slate-900"
						>
							{data.invoice.project_name}
						</a>
					</div>
				{/if}
			</div>
		</div>

		<!-- Line Items Table -->
		<div class="py-6 overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200 text-xs">
				<thead>
					<tr class="text-slate-500 font-bold uppercase tracking-wider text-[10px]">
						<th scope="col" class="py-2.5 text-left">Description</th>
						<th scope="col" class="py-2.5 text-right">Qty</th>
						<th scope="col" class="py-2.5 text-right">Unit Price</th>
						<th scope="col" class="py-2.5 text-right">Amount</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-100">
					{#each data.invoice.line_items as item (item.id)}
						<tr>
							<td class="py-3 text-slate-900 font-medium">
								{item.description}
								{#if item.service_name}
									<span class="block text-[11px] text-slate-500">{item.service_name}</span>
								{/if}
							</td>
							<td class="py-3 text-right text-slate-700 font-mono">
								{item.quantity ?? 1}
							</td>
							<td class="py-3 text-right text-slate-700 font-mono">
								{fmtPrice(item.unit_price ?? item.amount)}
							</td>
							<td class="py-3 text-right text-slate-900 font-bold font-mono">
								{fmtPrice(item.amount)}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Financial Summary Breakdown (Full Width) -->
		<div class="border-t border-slate-200 pt-6 space-y-4">
			<div class="w-full space-y-2 text-xs">
				<div class="flex justify-between items-center text-slate-600">
					<span class="font-medium">Subtotal</span>
					<span class="font-mono font-medium">{fmtPrice(data.invoice.subtotal)}</span>
				</div>
				{#if Number(data.invoice.tax_total) > 0}
					<div class="flex justify-between items-center text-slate-600">
						<span class="font-medium">Tax</span>
						<span class="font-mono font-medium">{fmtPrice(data.invoice.tax_total)}</span>
					</div>
				{/if}
				<div class="flex justify-between items-center text-sm font-bold text-slate-900 border-t border-slate-200 pt-2 pb-1">
					<span>Total</span>
					<span class="font-mono">{fmtPrice(data.invoice.total)}</span>
				</div>

				<!-- Itemized Payment Transaction Breakdown (Full Width) -->
				{#if data.transactions && data.transactions.length > 0}
					<div class="pt-2 border-t border-slate-100 space-y-2">
						{#each data.transactions as tx (tx.id)}
							{@const isDebit = tx.direction === 'debit'}
							<div class="flex justify-between items-center text-xs {isDebit ? 'text-emerald-700' : 'text-red-600'}">
								<span class="font-medium pr-4">
									{formatDate(tx.recorded_at)} · {isDebit ? 'Payment' : 'Refund'} ({humanize(tx.method)})
									{#if tx.reference_note}
										<span class="text-slate-500 font-normal">({tx.reference_note})</span>
									{/if}
								</span>
								<span class="font-mono font-semibold whitespace-nowrap">
									{isDebit ? '−' : '+'}{fmtPrice(tx.amount)}
								</span>
							</div>
						{/each}
					</div>
				{:else if Number(data.invoice.paid_amount) > 0}
					<div class="flex justify-between items-center text-emerald-600 font-medium pt-1 text-xs">
						<span>Amount Paid</span>
						<span class="font-mono">−{fmtPrice(data.invoice.paid_amount)}</span>
					</div>
				{/if}

				<div class="flex justify-between items-center text-sm font-bold {balanceDue > 0 ? 'text-amber-600' : 'text-slate-900'} border-t border-dashed border-slate-200 pt-2">
					<span>Balance Due</span>
					<span class="font-mono">{fmtPrice(balanceDue)}</span>
				</div>
				{#if advanceCredit > 0}
					<div class="flex justify-between items-center text-xs font-semibold text-emerald-700 pt-1">
						<span>Advance Credit / Overpayment</span>
						<span class="font-mono">+{fmtPrice(advanceCredit)}</span>
					</div>
				{/if}
			</div>

			{#if data.invoice.notes}
				<div class="pt-4 border-t border-slate-100 text-xs text-slate-600">
					<h4 class="font-bold text-slate-900 uppercase text-[10px] tracking-wider mb-1">Notes & Terms</h4>
					<p class="whitespace-pre-wrap">{data.invoice.notes}</p>
				</div>
			{/if}
		</div>
	</article>
</div>

<style>
	@media print {
		:global(body) {
			background: white !important;
			color: #0f172a !important;
		}
		:global(header),
		:global(aside),
		:global(nav),
		:global(.print\\:hidden) {
			display: none !important;
		}
		:global(main) {
			padding: 0 !important;
			margin: 0 !important;
			max-width: 100% !important;
			width: 100% !important;
		}
		#printable-invoice {
			box-shadow: none !important;
			border: none !important;
			padding: 0 !important;
			margin: 0 !important;
			width: 100% !important;
			max-width: 100% !important;
		}
	}
</style>
