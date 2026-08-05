<script>
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { Dialog } from 'bits-ui';
	import { ApiError } from '$lib/api/client.js';
	import * as invoiceApi from '$lib/api/invoices.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, formatDateTime, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);

	/** @type {string|null} */
	let actionErr = $state(null);
	/** @type {string|null} */
	let actionMsg = $state(null);

	let issueOpen = $state(false);
	let issueBusy = $state(false);
	let deleteOpen = $state(false);
	let deleteBusy = $state(false);
	let voidOpen = $state(false);
	let voidBusy = $state(false);

	// ---- FEAT-015: apply advance + refund ----
	let applyOpen = $state(false);
	let applyBusy = $state(false);
	/** @type {string|null} */
	let applyErr = $state(null);
	/** @type {string} */
	let applyAmount = $state('');

	let refundOpen = $state(false);
	let refundBusy = $state(false);
	/** @type {string|null} */
	let refundErr = $state(null);
	/** @type {string} */
	let refundAmount = $state('');
	/** @type {'bank_transfer'|'card'|'cash'|'other'} */
	let refundMethod = $state('other');
	/** @type {string} */
	let refundRef = $state('');

	const number = $derived(data.invoice.invoice_number ?? 'Draft');

	/** @type {string|null} */
	let pdfErr = $state(null);
	let downloading = $state(false);
	let viewing = $state(false);

	async function downloadPdf() {
		if (downloading) return;
		downloading = true;
		pdfErr = null;
		try {
			const filename = `${data.invoice.invoice_number ?? 'invoice'}.pdf`;
			await invoiceApi.downloadInvoicePdf(fetch, token, data.invoice.id, filename);
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
			await invoiceApi.viewInvoicePdf(fetch, token, data.invoice.id, filename);
		} catch (e) {
			pdfErr = e instanceof ApiError ? e.message : 'Could not open the invoice PDF.';
		} finally {
			viewing = false;
		}
	}

	async function runIssue() {
		issueBusy = true;
		actionErr = null;
		actionMsg = null;
		try {
			await invoiceApi.issueInvoice(fetch, token, data.invoice.id);
			issueOpen = false;
			actionMsg = 'Invoice issued.';
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not issue invoice.';
		} finally {
			issueBusy = false;
		}
	}

	async function runDelete() {
		deleteBusy = true;
		actionErr = null;
		actionMsg = null;
		try {
			await invoiceApi.deleteInvoice(fetch, token, data.invoice.id);
			deleteOpen = false;
			goto(resolve('/app/invoices'));
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not delete invoice.';
		} finally {
			deleteBusy = false;
		}
	}

	async function runVoid() {
		voidBusy = true;
		actionErr = null;
		actionMsg = null;
		try {
			await invoiceApi.voidInvoice(fetch, token, data.invoice.id);
			voidOpen = false;
			actionMsg = 'Invoice voided.';
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not void invoice.';
		} finally {
			voidBusy = false;
		}
	}

	async function runApplyAdvance() {
		applyErr = null;
		actionErr = null;
		actionMsg = null;
		const trimmed = applyAmount.trim();
		if (trimmed && Math.round((Number(trimmed) || 0) * 100) <= 0) {
			applyErr = 'Enter an amount greater than zero, or leave it empty for the full balance.';
			return;
		}
		applyBusy = true;
		try {
			const result = await invoiceApi.applyAdvance(
				fetch,
				token,
				data.invoice.id,
				trimmed || undefined
			);
			applyOpen = false;
			actionMsg = `Applied ${fmtPrice(result.applied)} · remaining advance ${fmtPrice(result.advance_balance)}`;
			await invalidateAll();
		} catch (e) {
			applyErr = e instanceof ApiError ? e.message : 'Could not apply advance.';
		} finally {
			applyBusy = false;
		}
	}

	async function runRefund() {
		refundErr = null;
		actionErr = null;
		actionMsg = null;
		if (!refundAmount || Math.round((Number(refundAmount) || 0) * 100) <= 0) {
			refundErr = 'Enter an amount greater than zero.';
			return;
		}
		refundBusy = true;
		try {
			/** @type {Record<string, any>} */
			const body = {
				amount: Number(refundAmount).toFixed(2),
				method: refundMethod
			};
			if (refundRef.trim()) body.reference_note = refundRef.trim();
			await invoiceApi.refundInvoice(fetch, token, data.invoice.id, /** @type {any} */ (body));
			refundOpen = false;
			actionMsg = 'Refund recorded.';
			await invalidateAll();
		} catch (e) {
			refundErr = e instanceof ApiError ? e.message : 'Could not record refund.';
		} finally {
			refundBusy = false;
		}
	}

	// ---- transactions (TODO-091 record payment, TODO-094 allocation override) ----
	let payOpen = $state(false);
	let payBusy = $state(false);
	/** @type {string|null} */
	let payErr = $state(null);
	/** @type {string} */
	let payAmount = $state('');
	/** @type {'bank_transfer'|'card'|'cash'|'other'} */
	let payMethod = $state('bank_transfer');
	/** @type {string} */
	let payRef = $state('');
	/** @type {string} */
	let payRecordedAt = $state('');
	/** @type {'auto'|'manual'} */
	let allocMode = $state('auto');
	/** @type {Record<string, string>} */
	let allocValues = $state({});

	const methodOptions = ['bank_transfer', 'card', 'cash', 'other'];
	const lineItems = $derived(data.invoice.line_items);
	const totalPaid = $derived(
		data.transactions.reduce(
			(sum, t) => sum + (Number(t.amount) || 0) * (t.direction === 'credit' ? -1 : 1),
			0
		)
	);
	const balanceDue = $derived(Math.max(0, (Number(data.invoice.total) || 0) - totalPaid));

	function openPay() {
		payErr = null;
		payAmount = '';
		payMethod = 'bank_transfer';
		payRef = '';
		payRecordedAt = '';
		allocMode = 'auto';
		allocValues = {};
		payOpen = true;
	}

	/**
	 * @param {string} lineItemId
	 */
	function descriptionOf(lineItemId) {
		return data.invoice.line_items.find((li) => li.id === lineItemId)?.description ?? 'Line item';
	}

	async function submitPay() {
		payErr = null;
		/** @param {string} v */
		const toCents = (v) => Math.round((Number(v) || 0) * 100);
		const amountCents = toCents(payAmount);
		if (!payAmount || amountCents <= 0) {
			payErr = 'Enter an amount greater than zero.';
			return;
		}
		/** @type {Array<{ line_item_id: string, amount: string }>|null} */
		let allocations = null;
		if (lineItems.length > 1 && allocMode === 'manual') {
			allocations = lineItems
				.map((li) => ({
					line_item_id: li.id,
					amount: (allocValues[li.id] ?? '').trim()
				}))
				.filter((a) => a.amount !== '');
			const sumCents = allocations.reduce((sum, a) => sum + toCents(a.amount), 0);
			if (sumCents !== amountCents) {
				payErr = 'Allocations must sum to the payment amount.';
				return;
			}
		}
		payBusy = true;
		try {
			/** @type {Record<string, any>} */
			const body = {
				amount: Number(payAmount).toFixed(2),
				method: payMethod
			};
			if (payRef.trim()) body.reference_note = payRef.trim();
			if (payRecordedAt) body.recorded_at = payRecordedAt;
			if (allocations) {
				body.allocations = allocations.map((a) => ({
					line_item_id: a.line_item_id,
					amount: Number(a.amount).toFixed(2)
				}));
			}
			await invoiceApi.recordTransaction(fetch, token, data.invoice.id, /** @type {any} */ (body));
			payOpen = false;
			await invalidateAll();
		} catch (e) {
			payErr = e instanceof ApiError ? e.message : 'Could not record payment.';
		} finally {
			payBusy = false;
		}
	}
</script>

<svelte:head><title>{number} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/invoices')} class="hover:text-indigo-600">Invoices</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">{number}</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div class="flex items-center gap-3">
		<h1 class="text-2xl font-semibold text-slate-900">{number}</h1>
		<StatusBadge status={data.invoice.status} />
		{#if data.invoice.project_id == null}
			<span
				class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-500/20 ring-inset"
			>
				Internal invoice
			</span>
		{/if}
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
		{#if data.invoice.status === 'draft'}
			<a
				href={resolve('/app/invoices/[id]/edit', { id: data.invoice.id })}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Edit
			</a>
			<button
				type="button"
				onclick={() => (issueOpen = true)}
				class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Issue
			</button>
			<button
				type="button"
				onclick={() => (deleteOpen = true)}
				class="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
			>
				Delete
			</button>
		{:else if data.invoice.status === 'issued' || data.invoice.status === 'partially_paid' || data.invoice.status === 'paid'}
			{#if data.invoice.status === 'issued' || data.invoice.status === 'partially_paid'}
				<button
					type="button"
					onclick={() => (applyOpen = true)}
					disabled={applyBusy}
					class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					Apply advance
				</button>
			{/if}
			{#if data.invoice.status === 'partially_paid' || data.invoice.status === 'paid'}
				<button
					type="button"
					onclick={() => (refundOpen = true)}
					disabled={refundBusy}
					class="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					Refund
				</button>
			{/if}
			<button
				type="button"
				onclick={() => (voidOpen = true)}
				class="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
			>
				Void
			</button>
		{/if}
	</div>
</div>

{#if actionErr}
	<p
		role="alert"
		class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{actionErr}
	</p>
{/if}
{#if actionMsg}
	<p
		role="status"
		class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
	>
		{actionMsg}
	</p>
{/if}

{#if pdfErr}
	<p
		role="alert"
		class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{pdfErr}
	</p>
{/if}

{#if data.invoice.status === 'void'}
	<section
		class="mt-6 rounded-lg border-2 border-dashed border-amber-300 bg-amber-50 p-5"
		aria-labelledby="void-correction-h"
	>
		<h2 id="void-correction-h" class="text-sm font-semibold text-amber-900">
			Correcting a voided invoice
		</h2>
		<p class="mt-1 text-sm text-amber-800">
			This invoice was voided. Corrections are made with a new invoice — financial history is never
			edited.
		</p>
		<div class="mt-3">
			<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
			<a
				href={data.invoice.project_id
					? `${resolve('/app/invoices/new')}?project_id=${data.invoice.project_id}`
					: resolve('/app/invoices/new')}
				class="rounded-md border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium text-amber-900 hover:bg-amber-100 focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:outline-none"
			>
				Create new invoice
			</a>
			<!-- eslint-enable svelte/no-navigation-without-resolve -->
		</div>
	</section>
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
		</dl>
	</section>
</div>

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
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<div class="flex flex-wrap items-center gap-2">
									{li.description}
									{#if li.project_service_id}
										<span
											class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-500/20 ring-inset"
											>from service</span
										>
									{/if}
								</div>
							</td>
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
	<div class="flex items-center justify-between border-b border-slate-200 px-6 py-4">
		<div>
			<h2 id="transactions-h" class="text-base font-semibold text-slate-900">Transactions</h2>
			<p class="mt-0.5 text-sm text-slate-500">
				{data.transactions.length}
				{data.transactions.length === 1 ? 'payment' : 'payments'} recorded
			</p>
		</div>
		{#if data.invoice.status === 'issued' || data.invoice.status === 'partially_paid'}
			<button
				type="button"
				onclick={openPay}
				class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Record payment
			</button>
		{/if}
	</div>
	<dl class="grid gap-4 border-b border-slate-200 bg-slate-50 px-6 py-4 sm:grid-cols-2">
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total paid</dt>
			<dd class="mt-1 text-sm font-semibold text-slate-900">{fmtPrice(totalPaid)}</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Balance due</dt>
			<dd class="mt-1 text-sm font-semibold text-slate-900">{fmtPrice(balanceDue)}</dd>
		</div>
	</dl>
	{#if data.transactions.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No payments recorded yet.</p>
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
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<ConfirmDialog
	bind:open={issueOpen}
	title="Issue invoice"
	description={`Mark invoice ${number} as issued? It can no longer be edited.`}
	confirmLabel="Issue invoice"
	busy={issueBusy}
	onconfirm={runIssue}
/>

<ConfirmDialog
	bind:open={deleteOpen}
	title="Delete invoice"
	description={`Permanently delete draft invoice ${number}? This cannot be undone.`}
	confirmLabel="Delete"
	destructive
	busy={deleteBusy}
	onconfirm={runDelete}
/>

<ConfirmDialog
	bind:open={voidOpen}
	title="Void invoice"
	description={`Void invoice ${number}? It stays on record with total $0.00 and can no longer be collected.`}
	confirmLabel="Void"
	destructive
	busy={voidBusy}
	onconfirm={runVoid}
/>

<!-- Record payment dialog (bits-ui Dialog) -->
<Dialog.Root bind:open={payOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Record payment</Dialog.Title>
				<Dialog.Close
					type="button"
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Record a payment against invoice {number}.
			</Dialog.Description>

			{#if payErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{payErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitPay();
				}}
			>
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label for="pay-amount" class="block text-sm font-medium text-slate-700">Amount</label>
						<input
							id="pay-amount"
							type="number"
							min="0.01"
							step="0.01"
							required
							bind:value={payAmount}
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
					<div>
						<label for="pay-method" class="block text-sm font-medium text-slate-700">Method</label>
						<select
							id="pay-method"
							bind:value={payMethod}
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						>
							{#each methodOptions as m (m)}
								<option value={m}>{humanize(m)}</option>
							{/each}
						</select>
					</div>
				</div>

				<div>
					<label for="pay-ref" class="block text-sm font-medium text-slate-700"
						>Reference note</label
					>
					<input
						id="pay-ref"
						type="text"
						bind:value={payRef}
						placeholder="Check number, transfer reference, …"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div>
					<label for="pay-date" class="block text-sm font-medium text-slate-700">Date</label>
					<input
						id="pay-date"
						type="datetime-local"
						bind:value={payRecordedAt}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-xs text-slate-500">Leave empty to use the current time.</p>
				</div>

				{#if lineItems.length > 1}
					<fieldset>
						<legend class="text-sm font-medium text-slate-700">Allocation</legend>
						<div class="mt-2 flex gap-4">
							<label class="flex items-center gap-2 text-sm text-slate-700">
								<input
									type="radio"
									name="alloc-mode"
									value="auto"
									bind:group={allocMode}
									class="text-indigo-600 focus:ring-indigo-500"
								/>
								Auto
							</label>
							<label class="flex items-center gap-2 text-sm text-slate-700">
								<input
									type="radio"
									name="alloc-mode"
									value="manual"
									bind:group={allocMode}
									class="text-indigo-600 focus:ring-indigo-500"
								/>
								Manual
							</label>
						</div>
						{#if allocMode === 'manual'}
							<div class="mt-3 overflow-hidden rounded-md border border-slate-200">
								<table class="min-w-full divide-y divide-slate-200">
									<thead class="bg-slate-50">
										<tr>
											<th
												scope="col"
												class="px-4 py-2 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
												>Line item</th
											>
											<th
												scope="col"
												class="px-4 py-2 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
												>Owed</th
											>
											<th
												scope="col"
												class="px-4 py-2 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
												>Amount</th
											>
										</tr>
									</thead>
									<tbody class="divide-y divide-slate-200">
										{#each lineItems as li (li.id)}
											<tr>
												<td class="px-4 py-2 text-sm text-slate-900">{li.description}</td>
												<td class="px-4 py-2 text-right text-sm whitespace-nowrap text-slate-700"
													>{fmtPrice(li.amount)}</td
												>
												<td class="px-4 py-2 text-right">
													<input
														type="number"
														min="0"
														step="0.01"
														placeholder="0.00"
														value={allocValues[li.id] ?? ''}
														oninput={(e) =>
															(allocValues[li.id] = /** @type {HTMLInputElement} */ (
																e.currentTarget
															).value)}
														class="w-32 rounded-md border-slate-300 text-right text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
													/>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}
					</fieldset>
				{/if}

				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={payBusy}
						aria-busy={payBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if payBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Record payment
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Apply advance dialog -->
<Dialog.Root bind:open={applyOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Apply advance</Dialog.Title>
				<Dialog.Close
					type="button"
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Apply the client's advance balance to invoice {number}.
			</Dialog.Description>

			{#if applyErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{applyErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					runApplyAdvance();
				}}
			>
				<div>
					<label for="apply-amount" class="block text-sm font-medium text-slate-700">Amount</label>
					<input
						id="apply-amount"
						type="number"
						min="0.01"
						step="0.01"
						bind:value={applyAmount}
						placeholder="Full available balance"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-xs text-slate-500">
						Leave empty to apply the full available advance balance.
					</p>
				</div>

				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={applyBusy}
						aria-busy={applyBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if applyBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Apply advance
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Refund dialog -->
<Dialog.Root bind:open={refundOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Refund</Dialog.Title>
				<Dialog.Close
					type="button"
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Record a refund against invoice {number}. This reduces the paid amount on record.
			</Dialog.Description>

			{#if refundErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{refundErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					runRefund();
				}}
			>
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label for="refund-amount" class="block text-sm font-medium text-slate-700"
							>Amount</label
						>
						<input
							id="refund-amount"
							type="number"
							min="0.01"
							step="0.01"
							required
							bind:value={refundAmount}
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
					<div>
						<label for="refund-method" class="block text-sm font-medium text-slate-700"
							>Method</label
						>
						<select
							id="refund-method"
							bind:value={refundMethod}
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						>
							{#each methodOptions as m (m)}
								<option value={m}>{humanize(m)}</option>
							{/each}
						</select>
					</div>
				</div>

				<div>
					<label for="refund-ref" class="block text-sm font-medium text-slate-700"
						>Reference note</label
					>
					<input
						id="refund-ref"
						type="text"
						bind:value={refundRef}
						placeholder="Refund reason, transfer reference, …"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={refundBusy}
						aria-busy={refundBusy}
						class="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if refundBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Record refund
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
