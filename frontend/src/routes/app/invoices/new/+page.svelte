<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Icon from '@iconify/svelte';
	import trashCanOutline from '@iconify-icons/mdi/trash-can-outline';
	import plus from '@iconify-icons/mdi/plus';
	import { ApiError } from '$lib/api/client.js';
	import * as invoiceApi from '$lib/api/invoices.js';
	import * as projectApi from '$lib/api/projects.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { fmtPrice } from '$lib/utils/format.js';

	let { data } = $props();

	const token = auth.token;

	let projectId = $state(untrack(() => data.initialProjectId));
	let issueDate = $state(null);
	let dueDate = $state(null);
	let notes = $state('');
	let projectServices = $state([]);
	let loadedProjectId = $state(null);
	let servicesLoading = $state(false);
	let servicesErr = $state(null);
	let projectLedger = $state(null);

	let rowKey = 1;
	const today = new Date().toISOString().slice(0, 10);
	let rows = $state([]);
	let busy = $state(false);
	let err = $state(null);

	$effect(() => {
		if (projectId && projectId !== loadedProjectId) {
			loadServices();
		} else if (!projectId) {
			projectServices = [];
			rows = [];
			projectLedger = null;
		}
	});

	async function loadServices() {
		servicesLoading = true;
		servicesErr = null;
		try {
			const [project, ledger] = await Promise.all([
				projectApi.getProject(fetch, token, projectId),
				projectApi.getProjectLedger(fetch, token, projectId).catch(() => null)
			]);
			projectServices = project.services.filter((s) => s.status === 'active');
			projectLedger = ledger;
			loadedProjectId = projectId;
			rows = [];
		} catch (e) {
			servicesErr = e instanceof ApiError ? e.message : 'Could not load project services.';
		} finally {
			servicesLoading = false;
		}
	}

	function addRow() {
		rows.push({
			key: rowKey++,
			kind: projectId ? 'service' : 'custom',
			project_service_id: '',
			service_name: '',
			unit_price: '',
			quantity: 1,
			description: '',
			entry_date: today
		});
	}

	function removeRow(key) {
		rows = rows.filter((r) => r.key !== key);
	}

	function onRowServiceChange(row, psId) {
		row.project_service_id = psId;
		const ps = projectServices.find((s) => s.id === psId);
		row.service_name = ps?.service_name ?? '';
		row.unit_price = ps?.price_at_attachment ?? '';
	}

	let subtotal = $derived.by(() =>
		rows.reduce((sum, r) => sum + r.quantity * (Number(r.unit_price) || 0), 0)
	);

	let invoicedByService = $derived.by(() => {
		const map = {};
		for (const e of projectLedger?.entries ?? []) {
			if (
				e.type !== 'charge' ||
				!e.invoice_number ||
				e.source_type !== 'project_service' ||
				!e.source_id
			) {
				continue;
			}
			(map[e.source_id] ??= []).push(e.invoice_number);
		}
		for (const k of Object.keys(map)) map[k] = [...new Set(map[k])];
		return map;
	});

	function invoicedFlag(psId) {
		const nums = invoicedByService[psId];
		if (!nums || nums.length === 0) return null;
		const head = nums[0];
		return nums.length > 1 ? `Invoiced — ${head} +${nums.length - 1} more` : `Invoiced — ${head}`;
	}

	let discount = $derived.by(() => {
		const s = projectLedger?.summary;
		if (!s) return null;
		const type = s.discount_type;
		if (type !== 'percentage' && type !== 'fixed') return null;
		if (!(subtotal > 0)) return null;
		const v = Number(s.discount_value) || 0;
		if (!(v > 0)) return null;
		const amount =
			type === 'percentage' ? Math.round(subtotal * (v / 100) * 100) / 100 : Math.min(v, subtotal);
		if (!(amount > 0)) return null;
		return { amount, label: `Discount (${type} ${s.discount_value})` };
	});

	let total = $derived(subtotal - (discount?.amount ?? 0));

	async function submit() {
		err = null;
		if (rows.length === 0) {
			err = 'Add at least one line item.';
			return;
		}
		for (const r of rows) {
			if (!projectId && r.kind === 'service') {
				err = 'Project services need a project. Switch the row to Custom.';
				return;
			}
			if (r.kind === 'service' && !r.project_service_id) {
				err = 'Every line item needs a service.';
				return;
			}
			if (r.kind === 'custom') {
				if (!r.description.trim()) {
					err = 'Every custom line item needs a description.';
					return;
				}
				if (r.unit_price === '' || Number(r.unit_price) < 0) {
					err = 'Every custom line item needs a unit price.';
					return;
				}
			}
		}
		busy = true;
		try {
			const body = {
				line_items: rows.map((r) => {
					const item = {};
					if (r.entry_date) item.entry_date = r.entry_date;
					if (r.kind === 'service') {
						item.project_service_id = r.project_service_id;
					} else {
						item.description = r.description.trim();
						item.unit_price = String(r.unit_price);
						item.quantity = r.quantity || 1;
					}
					return item;
				})
			};
			if (discount) {
				body.line_items.push({
					description: discount.label,
					unit_price: String(-discount.amount),
					quantity: 1
				});
			}
			if (projectId) body.project_id = projectId;
			if (issueDate) body.issue_date = issueDate;
			if (dueDate) body.due_date = dueDate;
			if (notes.trim()) body.notes = notes.trim();
			const created = await invoiceApi.createInvoice(fetch, token, body);
			goto(resolve('/app/invoices/[id]', { id: created.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Create failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>New invoice — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/invoices')} class="hover:text-indigo-600">Invoices</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">New</li>
	</ol>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">New invoice</h1>

{#if err}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{err}
	</p>
{/if}

<form
	class="mt-6 w-full space-y-6"
	onsubmit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<section class="space-y-4">
		<div class="grid gap-4 sm:grid-cols-3">
			<div>
				<label for="i-project" class="block text-sm font-medium text-slate-700">Project</label>
				<select
					id="i-project"
					bind:value={projectId}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				>
					<option value="" disabled>Select a project</option>
					<option value="">— General / internal invoice (no project) —</option>
					{#each data.projects as p (p.id)}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
				{#if !projectId}
					<p class="mt-1 text-xs text-slate-500">
						General (internal) invoice: custom line items only. Not visible to clients.
					</p>
				{/if}
			</div>
			<div>
				<label for="i-issue" class="block text-sm font-medium text-slate-700">Issue date</label>
				<input
					id="i-issue"
					type="date"
					bind:value={issueDate}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="i-due" class="block text-sm font-medium text-slate-700">Due date</label>
				<input
					id="i-due"
					type="date"
					bind:value={dueDate}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
		</div>

		<div>
			<label for="i-notes" class="block text-sm font-medium text-slate-700">Notes</label>
			<textarea
				id="i-notes"
				bind:value={notes}
				rows="3"
				placeholder="Payment terms, thank-you note, …"
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			></textarea>
		</div>
	</section>

	<section
		class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs"
		aria-labelledby="line-items-h"
	>
		<div class="flex items-center justify-between">
			<div>
				<h2 id="line-items-h" class="text-sm font-bold text-slate-900">Line Items *</h2>
				<p class="mt-0.5 text-xs text-slate-500">
					Pick a project service to bill at its attached price, or add custom line items.
				</p>
			</div>
			<button
				type="button"
				onclick={addRow}
				class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
			>
				<Icon icon={plus} class="h-3.5 w-3.5" />
				Add Item
			</button>
		</div>

		{#if servicesErr}
			<p
				role="alert"
				class="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800"
			>
				{servicesErr}
			</p>
		{/if}

		{#if projectId && servicesLoading}
			<div class="mt-3 flex items-center gap-2 text-xs text-slate-600">
				<Spinner class="h-3.5 w-3.5 text-indigo-600" /> Loading project services…
			</div>
		{:else if projectId && projectServices.length === 0}
			<p class="mt-3 text-xs text-slate-500">
				This project has no active services. Add custom lines instead, or attach services on the
				project page.
			</p>
		{/if}

		<div class="mt-4 space-y-2.5">
			{#each rows as row (row.key)}
				{@const amount = row.quantity * (Number(row.unit_price) || 0)}
				<div class="rounded-xl border border-slate-200 bg-slate-50/70 p-3 transition-colors hover:border-slate-300">
					<div class="flex flex-wrap lg:flex-nowrap items-end gap-2.5">
						<!-- Date -->
						<div class="w-full sm:w-32 shrink-0">
							<label for={`li-date-${row.key}`} class="block text-[11px] font-semibold text-slate-600 mb-1">
								Date
							</label>
							<input
								id={`li-date-${row.key}`}
								type="date"
								bind:value={row.entry_date}
								class="block w-full rounded-lg border-slate-300 py-1.5 px-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>

						<!-- Type -->
						<div class="w-full sm:w-28 shrink-0">
							<label for={`li-kind-${row.key}`} class="block text-[11px] font-semibold text-slate-600 mb-1">
								Type
							</label>
							<select
								id={`li-kind-${row.key}`}
								bind:value={row.kind}
								class="block w-full rounded-lg border-slate-300 py-1.5 px-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							>
								{#if projectId}
									<option value="service">Service</option>
								{/if}
								<option value="custom">Custom</option>
							</select>
						</div>

						<!-- Service Select or Description Input -->
						{#if row.kind === 'service'}
							<div class="flex-1 min-w-[180px]">
								<label for={`li-service-${row.key}`} class="block text-[11px] font-semibold text-slate-600 mb-1">
									Project Service *
								</label>
								<select
									id={`li-service-${row.key}`}
									value={row.project_service_id}
									onchange={(e) => onRowServiceChange(row, e.currentTarget.value)}
									class="block w-full rounded-lg border-slate-300 py-1.5 px-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
								>
									<option value="" disabled>Select a service</option>
									{#each projectServices as ps (ps.id)}
										{@const flag = invoicedFlag(ps.id)}
										<option value={ps.id}>
											{ps.service_name}{flag ? ` — ${flag}` : ''}
										</option>
									{/each}
								</select>
							</div>
							<div class="w-28 shrink-0">
								<span class="block text-[11px] font-semibold text-slate-600 mb-1">Unit Price</span>
								<div class="rounded-lg border border-slate-200 bg-white py-1.5 px-2.5 text-xs font-mono text-slate-700 h-[34px] flex items-center">
									{row.unit_price === '' ? '—' : fmtPrice(row.unit_price)}
								</div>
							</div>
						{:else}
							<div class="flex-1 min-w-[180px]">
								<label for={`li-desc-${row.key}`} class="block text-[11px] font-semibold text-slate-600 mb-1">
									Description *
								</label>
								<input
									id={`li-desc-${row.key}`}
									type="text"
									bind:value={row.description}
									placeholder="e.g. Consulting, Design, Development"
									class="block w-full rounded-lg border-slate-300 py-1.5 px-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
								/>
							</div>
							<div class="w-28 shrink-0">
								<label for={`li-price-${row.key}`} class="block text-[11px] font-semibold text-slate-600 mb-1">
									Unit Price *
								</label>
								<input
									id={`li-price-${row.key}`}
									type="number"
									min="0"
									step="0.01"
									bind:value={row.unit_price}
									placeholder="0.00"
									class="block w-full rounded-lg border-slate-300 py-1.5 px-2.5 text-xs font-mono shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
								/>
							</div>
						{/if}

						<!-- Quantity -->
						<div class="w-16 shrink-0">
							<label for={`li-qty-${row.key}`} class="block text-[11px] font-semibold text-slate-600 mb-1">
								Qty
							</label>
							<input
								id={`li-qty-${row.key}`}
								type="number"
								min="1"
								step="1"
								bind:value={row.quantity}
								class="block w-full rounded-lg border-slate-300 py-1.5 px-2 text-xs font-mono text-center shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>

						<!-- Amount -->
						<div class="w-28 shrink-0">
							<span class="block text-[11px] font-semibold text-slate-600 mb-1 text-right">Amount</span>
							<div class="rounded-lg border border-slate-200 bg-white py-1.5 px-2.5 text-xs font-mono font-bold text-slate-900 text-right h-[34px] flex items-center justify-end">
								{fmtPrice(amount)}
							</div>
						</div>

						<!-- Action: Remove Icon Button -->
						<div class="shrink-0 pb-0.5">
							<button
								type="button"
								onclick={() => removeRow(row.key)}
								aria-label="Remove line item"
								title="Remove item"
								class="inline-flex h-[34px] w-[34px] items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-400 hover:border-red-200 hover:bg-red-50 hover:text-red-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 shadow-2xs"
							>
								<Icon icon={trashCanOutline} class="h-4 w-4" />
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<section
		class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
		aria-labelledby="totals-h"
	>
		<h2 id="totals-h" class="text-base font-semibold text-slate-900">Totals</h2>
		<dl class="mt-3 max-w-xs space-y-1 text-sm">
			<div class="flex justify-between">
				<dt class="text-slate-500">Subtotal</dt>
				<dd class="font-medium text-slate-900">{fmtPrice(subtotal)}</dd>
			</div>
			{#if discount}
				<div class="flex items-center justify-between gap-3">
					<dt class="flex items-center gap-2 text-slate-500">
						Discount
						<span
							class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
						>
							Project discount applied
						</span>
					</dt>
					<dd class="font-medium text-red-600">−{fmtPrice(discount.amount)}</dd>
				</div>
			{/if}
			<div class="flex justify-between">
				<dt class="text-slate-500">Tax</dt>
				<dd class="font-medium text-slate-900">{fmtPrice(0)}</dd>
			</div>
			<div class="flex justify-between border-t border-slate-200 pt-2">
				<dt class="font-medium text-slate-700">Total</dt>
				<dd class="font-semibold text-slate-900">{fmtPrice(total)}</dd>
			</div>
		</dl>
	</section>

	<div class="flex items-center gap-3 pt-2">
		<button
			type="submit"
			disabled={busy}
			aria-busy={busy}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
			Create invoice
		</button>
		<a
			href={resolve('/app/invoices')}
			class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Cancel
		</a>
	</div>
</form>
