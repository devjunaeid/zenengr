<script>
	import { invalidateAll } from '$app/navigation';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as invoiceApi from '$lib/api/invoices.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = auth.token;

	const statusOptions = ['', 'draft', 'issued', 'partially_paid', 'paid', 'void'];

	let newInvoiceHref = $derived(
		data.newInvoiceProjectId
			? `${resolve('/app/invoices/new')}?project_id=${data.newInvoiceProjectId}`
			: resolve('/app/invoices/new')
	);

	let actionErr = $state(null);
	let issueBusyId = $state(null);
	let voidTarget = $state(null);
	let voidBusy = $state(false);

	async function issueInvoice(invoice) {
		issueBusyId = invoice.id;
		actionErr = null;
		try {
			await invoiceApi.issueInvoice(fetch, token, invoice.id);
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not issue invoice.';
		} finally {
			issueBusyId = null;
		}
	}

	async function runVoid() {
		if (!voidTarget) return;
		voidBusy = true;
		actionErr = null;
		try {
			await invoiceApi.voidInvoice(fetch, token, voidTarget.id);
			voidTarget = null;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not void invoice.';
		} finally {
			voidBusy = false;
		}
	}

	function setStatus(s) {
		const params = new SvelteURLSearchParams();
		if (s) params.set('status', s);
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL on the same page
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}

	function gotoPage(p) {
		const params = new SvelteURLSearchParams();
		if (data.filters.status) params.set('status', data.filters.status);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL on the same page
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}
</script>

<svelte:head><title>Invoices — {data.client.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/clients')} class="hover:text-indigo-600">Clients</a>
		</li>
		<li aria-hidden="true">/</li>
		<li>
			<a href={resolve('/app/clients/[id]', { id: data.client.id })} class="hover:text-indigo-600">
				{data.client.name}
			</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">Invoices</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Invoices</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.invoices.total}
			{data.invoices.total === 1 ? 'invoice' : 'invoices'} for {data.client.name}
		</p>
	</div>
	<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
	<a
		href={newInvoiceHref}
		class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		New invoice
	</a>
	<!-- eslint-enable svelte/no-navigation-without-resolve -->
</div>

{#if actionErr}
	<p
		role="alert"
		class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{actionErr}
	</p>
{/if}

<div class="mt-6 flex flex-wrap items-end gap-3">
	<div>
		<label for="f-status" class="block text-xs font-medium text-slate-600">Status</label>
		<select
			id="f-status"
			value={data.filters.status}
			onchange={(e) => setStatus(e.currentTarget.value)}
			class="mt-1 block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		>
			{#each statusOptions as opt (opt)}
				<option value={opt}>{opt === '' ? 'All' : humanize(opt)}</option>
			{/each}
		</select>
	</div>
</div>

<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	{#if data.invoices.items.length === 0}
		{#if data.filters.status}
			<p class="px-6 py-8 text-sm text-slate-500">
				No results match your filters. Try different filters.
			</p>
		{:else}
			<EmptyState title="No invoices yet" description="No invoices yet for this client.">
				<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
				<a
					href={newInvoiceHref}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					New invoice
				</a>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
			</EmptyState>
		{/if}
	{:else}
		<div class="relative overflow-x-auto">
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
							>Issue date</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Due date</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Actions</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.invoices.items as inv (inv.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/invoices/[id]', { id: inv.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{inv.invoice_number ?? '—'}
								</a>
							</td>
							<td class="px-4 py-3"><StatusBadge status={inv.status} /></td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(inv.total)}</td
							>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(inv.issue_date)}</td
							>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(inv.due_date)}</td
							>
							<td class="px-4 py-3">
								<div class="flex flex-wrap items-center gap-3">
									<a
										href={resolve('/app/invoices/[id]', { id: inv.id })}
										class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
									>
										View
									</a>
									{#if inv.status === 'draft'}
										<button
											type="button"
											disabled={issueBusyId === inv.id}
											aria-busy={issueBusyId === inv.id}
											onclick={() => issueInvoice(inv)}
											class="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
										>
											{#if issueBusyId === inv.id}
												<Spinner class="h-3.5 w-3.5 text-indigo-600" />{/if}
											Issue
										</button>
									{:else if inv.status === 'issued' || inv.status === 'partially_paid' || inv.status === 'paid'}
										<button
											type="button"
											onclick={() => (voidTarget = inv)}
											class="text-sm font-medium text-red-600 hover:text-red-500"
										>
											Void
										</button>
									{/if}
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

<ConfirmDialog
	bind:open={
		() => voidTarget !== null,
		(v) => {
			if (!v) voidTarget = null;
		}
	}
	title="Void invoice"
	description={voidTarget
		? `Void invoice ${voidTarget.invoice_number ?? 'draft'}? It stays on record with total $0.00 and can no longer be collected.`
		: ''}
	confirmLabel="Void"
	destructive
	busy={voidBusy}
	onconfirm={runVoid}
/>
