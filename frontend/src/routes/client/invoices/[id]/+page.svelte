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
			? data.transactions.reduce(
					(acc, tx) => acc + (tx.direction === 'debit' ? Number(tx.amount) : -Number(tx.amount)),
					0
				)
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

<div class="mx-auto max-w-4xl space-y-6">
	<!-- Action Bar (Hidden in print) -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between print:hidden">
		<nav aria-label="Breadcrumb" class="text-xs font-semibold text-slate-500">
			<ol class="flex items-center gap-1.5">
				<li>
					<a
						href={resolve('/client/invoices')}
						class="flex items-center gap-1 hover:text-indigo-600"
					>
						<Icon icon={arrowLeft} class="h-3.5 w-3.5" />
						Invoices
					</a>
				</li>
				<li aria-hidden="true" class="text-slate-300">/</li>
				<li class="font-bold text-slate-800">{number}</li>
			</ol>
		</nav>

		<div class="flex flex-wrap items-center gap-2">
			<button
				type="button"
				onclick={printInvoice}
				class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50"
			>
				<Icon icon={printerOutline} class="h-4 w-4 text-slate-500" />
				Print Invoice
			</button>
			<button
				type="button"
				onclick={downloadPdf}
				disabled={downloading}
				class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 disabled:opacity-60"
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
		<div
			role="alert"
			class="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 shadow-2xs print:hidden"
		>
			{pdfErr}
		</div>
	{/if}

	<!-- Printable Visual Invoice Document -->
	<article
		id="printable-invoice"
		class="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm sm:p-12 print:m-0 print:border-none print:p-0 print:shadow-none"
	>
		<!-- Header / Brand -->
		<div
			class="flex flex-col items-start justify-between gap-6 border-b border-slate-200 pb-8 sm:flex-row"
		>
			<div class="flex items-center gap-4">
				{#if data.invoice.tenant_logo_url}
					<img
						src={data.invoice.tenant_logo_url}
						alt={data.invoice.tenant_business_name || portalAuth.tenantName || 'Company Logo'}
						class="h-12 w-auto max-w-[180px] rounded object-contain"
					/>
				{/if}
				<div>
					<h2 class="text-2xl font-black tracking-tight text-slate-900">
						{data.invoice.tenant_business_name || portalAuth.tenantName || 'INVOICE'}
					</h2>
					<p class="mt-0.5 text-xs text-slate-500">Official Client Statement</p>
				</div>
			</div>

			<div class="text-left sm:text-right">
				<div class="inline-flex items-center gap-2">
					<span class="text-base font-bold text-slate-900">{number}</span>
					<StatusBadge status={data.invoice.status} />
				</div>
				<p class="mt-1 text-xs text-slate-500">
					Project: <span class="font-semibold text-slate-800"
						>{data.invoice.project_name || 'General Project'}</span
					>
				</p>
			</div>
		</div>

		<!-- Billing Info & Dates Grid -->
		<div class="grid grid-cols-1 gap-8 border-b border-slate-200 py-8 text-xs sm:grid-cols-2">
			<div>
				<h3 class="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Billed To</h3>
				<p class="mt-2 text-sm font-bold text-slate-900">{client.name}</p>
				{#if client.email}
					<p class="mt-0.5 text-slate-600">{client.email}</p>
				{/if}
				{#if client.phone}
					<p class="mt-0.5 text-slate-600">{client.phone}</p>
				{/if}
				{#if client.tax_id}
					<p class="mt-0.5 text-slate-600">Tax ID / VAT: {client.tax_id}</p>
				{/if}
			</div>

			<div class="space-y-1.5 sm:text-right">
				<div>
					<span class="text-slate-500">Issue Date:</span>
					<span class="ml-2 font-semibold text-slate-900"
						>{formatDate(data.invoice.issue_date)}</span
					>
				</div>
				<div>
					<span class="text-slate-500">Due Date:</span>
					<span class="ml-2 font-semibold text-slate-900">{formatDate(data.invoice.due_date)}</span>
				</div>
				{#if data.invoice.project_id}
					<div>
						<span class="text-slate-500">Project Reference:</span>
						<a
							href={resolve('/client/projects/[id]', { id: data.invoice.project_id })}
							class="ml-2 font-semibold text-indigo-600 hover:text-indigo-700 print:text-slate-900"
						>
							{data.invoice.project_name}
						</a>
					</div>
				{/if}
			</div>
		</div>

		<!-- Line Items (Cards on mobile < sm, Table on desktop >= sm) -->
		<div class="space-y-2.5 py-4 sm:hidden">
			{#each data.invoice.line_items as item (item.id)}
				<div class="rounded-xl border border-slate-200/90 bg-slate-50/50 p-3.5 space-y-2 shadow-2xs">
					<div class="flex items-start justify-between gap-2">
						<div class="min-w-0 flex-1">
							<p class="text-xs font-semibold text-slate-900">{item.description}</p>
							{#if item.service_name}
								<span class="block text-[11px] text-slate-500">{item.service_name}</span>
							{/if}
						</div>
						<span class="font-mono text-xs font-bold text-slate-900 shrink-0">{fmtPrice(item.amount)}</span>
					</div>
					<div class="flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-200/60 pt-1.5">
						<span>Qty: <strong class="font-mono text-slate-700">{item.quantity ?? 1}</strong></span>
						<span>Unit Price: <strong class="font-mono text-slate-700">{fmtPrice(item.unit_price ?? item.amount)}</strong></span>
					</div>
				</div>
			{/each}
		</div>

		<!-- Line Items Table (Desktop >= sm) -->
		<div class="hidden sm:block relative overflow-x-auto py-6">
			<table class="min-w-full divide-y divide-slate-200 text-xs">
				<thead>
					<tr class="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
						<th scope="col" class="py-2.5 text-left">Description</th>
						<th scope="col" class="py-2.5 text-right">Qty</th>
						<th scope="col" class="py-2.5 text-right">Unit Price</th>
						<th scope="col" class="py-2.5 text-right">Amount</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-100">
					{#each data.invoice.line_items as item (item.id)}
						<tr>
							<td class="py-3 font-medium text-slate-900">
								{item.description}
								{#if item.service_name}
									<span class="block text-[11px] text-slate-500">{item.service_name}</span>
								{/if}
							</td>
							<td class="py-3 text-right font-mono text-slate-700">
								{item.quantity ?? 1}
							</td>
							<td class="py-3 text-right font-mono text-slate-700">
								{fmtPrice(item.unit_price ?? item.amount)}
							</td>
							<td class="py-3 text-right font-mono font-bold text-slate-900">
								{fmtPrice(item.amount)}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Financial Summary Breakdown (Full Width) -->
		<div class="space-y-4 border-t border-slate-200 pt-6">
			<div class="w-full space-y-2 text-xs">
				<div class="flex items-center justify-between text-slate-600">
					<span class="font-medium">Subtotal</span>
					<span class="font-mono font-medium">{fmtPrice(data.invoice.subtotal)}</span>
				</div>
				{#if Number(data.invoice.tax_total) > 0}
					<div class="flex items-center justify-between text-slate-600">
						<span class="font-medium">Tax</span>
						<span class="font-mono font-medium">{fmtPrice(data.invoice.tax_total)}</span>
					</div>
				{/if}
				<div
					class="flex items-center justify-between border-t border-slate-200 pt-2 pb-1 text-sm font-bold text-slate-900"
				>
					<span>Total</span>
					<span class="font-mono">{fmtPrice(data.invoice.total)}</span>
				</div>

				<!-- Itemized Payment Transaction Breakdown (Full Width) -->
				{#if data.transactions && data.transactions.length > 0}
					<div class="space-y-2 border-t border-slate-100 pt-2">
						{#each data.transactions as tx (tx.id)}
							{@const isDebit = tx.direction === 'debit'}
							<div
								class="flex items-center justify-between text-xs {isDebit
									? 'text-emerald-700'
									: 'text-red-600'}"
							>
								<span class="pr-4 font-medium">
									{formatDate(tx.recorded_at)} · {isDebit ? 'Payment' : 'Refund'} ({humanize(
										tx.method
									)})
									{#if tx.reference_note}
										<span class="font-normal text-slate-500">({tx.reference_note})</span>
									{/if}
								</span>
								<span class="font-mono font-semibold whitespace-nowrap">
									{isDebit ? '−' : '+'}{fmtPrice(tx.amount)}
								</span>
							</div>
						{/each}
					</div>
				{:else if Number(data.invoice.paid_amount) > 0}
					<div class="flex items-center justify-between pt-1 text-xs font-medium text-emerald-600">
						<span>Amount Paid</span>
						<span class="font-mono">−{fmtPrice(data.invoice.paid_amount)}</span>
					</div>
				{/if}

				<div
					class="flex items-center justify-between text-sm font-bold {balanceDue > 0
						? 'text-amber-600'
						: 'text-slate-900'} border-t border-dashed border-slate-200 pt-2"
				>
					<span>Balance Due</span>
					<span class="font-mono">{fmtPrice(balanceDue)}</span>
				</div>
				{#if advanceCredit > 0}
					<div
						class="flex items-center justify-between pt-1 text-xs font-semibold text-emerald-700"
					>
						<span>Advance Credit / Overpayment</span>
						<span class="font-mono">+{fmtPrice(advanceCredit)}</span>
					</div>
				{/if}
			</div>

			{#if data.invoice.notes}
				<div class="border-t border-slate-100 pt-4 text-xs text-slate-600">
					<h4 class="mb-1 text-[10px] font-bold tracking-wider text-slate-900 uppercase">
						Notes & Terms
					</h4>
					<p class="whitespace-pre-wrap">{data.invoice.notes}</p>
				</div>
			{/if}
		</div>
	</article>
</div>

<style>
	@media print {
		@page {
			margin: 0;
			size: auto;
		}
		:global(html),
		:global(body) {
			background: #ffffff !important;
			color: #0f172a !important;
			margin: 0 !important;
			padding: 0 !important;
			-webkit-print-color-adjust: exact !important;
			print-color-adjust: exact !important;
		}
		:global(header),
		:global(aside),
		:global(nav),
		:global(footer),
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
			padding: 18mm 20mm !important;
			margin: 0 auto !important;
			width: 100% !important;
			max-width: 100% !important;
			display: block !important;
			page-break-inside: avoid;
		}
	}
</style>
