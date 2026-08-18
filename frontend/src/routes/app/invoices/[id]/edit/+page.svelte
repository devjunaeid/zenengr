<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as invoiceApi from '$lib/api/invoices.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { fmtPrice } from '$lib/utils/format.js';

	/**
	 * One editable line item row. `kind` switches between a billed project
	 * service and a custom description/price line. `id` is set for rows that
	 * already exist on the invoice so PATCH can target them.
	 * @typedef {object} LineItemRow
	 * @property {number} key
	 * @property {'service'|'custom'} kind
	 * @property {string|null} id
	 * @property {string} project_service_id '' for custom rows
	 * @property {string} service_name display name for service rows
	 * @property {number|string} unit_price decimal snapshot for service rows, input for custom
	 * @property {number} quantity
	 * @property {string} description
	 * @property {string} entry_date ISO date-only (YYYY-MM-DD)
	 */

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	const initial = untrack(() => data.invoice);

	let issueDate = $state(initial.issue_date);
	/** @type {string|null} */
	let dueDate = $state(initial.due_date);
	let notes = $state(initial.notes ?? '');
	/** @type {import('$lib/api/projects.js').ProjectServiceItem[]} */
	let projectServices = $state(untrack(() => data.project?.services ?? []));

	let rowKey = 1;
	/** Line item date defaults to today when the item has none. */
	const today = new Date().toISOString().slice(0, 10);
	/** @type {LineItemRow[]} */
	let rows = $state(
		initial.line_items.map((li) => ({
			key: rowKey++,
			kind: li.project_service_id ? 'service' : 'custom',
			id: li.id,
			project_service_id: li.project_service_id ?? '',
			service_name: li.description,
			unit_price: li.unit_price,
			quantity: li.quantity ?? 1,
			description: li.description,
			entry_date: li.entry_date ?? today
		}))
	);
	let busy = $state(false);
	/** @type {string|null} */
	let err = $state(null);

	function addRow() {
		rows.push({
			key: rowKey++,
			kind: data.project ? 'service' : 'custom',
			id: null,
			project_service_id: '',
			service_name: '',
			unit_price: '',
			quantity: 1,
			description: '',
			entry_date: today
		});
	}

	/**
	 * @param {number} key
	 */
	function removeRow(key) {
		rows = rows.filter((r) => r.key !== key);
	}

	/**
	 * @param {LineItemRow} row
	 * @param {string} psId
	 */
	function onRowServiceChange(row, psId) {
		row.project_service_id = psId;
		const ps = projectServices.find((s) => s.id === psId);
		row.service_name = ps?.service_name ?? row.service_name;
		row.unit_price = ps?.price_at_attachment ?? row.unit_price;
	}

	let subtotal = $derived.by(() =>
		rows.reduce((sum, r) => sum + r.quantity * (Number(r.unit_price) || 0), 0)
	);

	async function submit() {
		err = null;
		if (rows.length === 0) {
			err = 'Add at least one line item.';
			return;
		}
		for (const r of rows) {
			if (r.kind === 'service' && !data.project) {
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
			/** @type {Record<string, any>} */
			const body = {
				line_items: rows.map((r) => {
					/** @type {Record<string, any>} */
					const item = {};
					if (r.id) item.id = r.id;
					if (r.entry_date) item.entry_date = r.entry_date;
					if (r.kind === 'service') {
						item.project_service_id = r.project_service_id;
						item.quantity = r.quantity || 1;
					} else {
						item.description = r.description.trim();
						item.unit_price = String(r.unit_price);
						item.quantity = r.quantity || 1;
					}
					return item;
				})
			};
			if (issueDate) body.issue_date = issueDate;
			if (dueDate) body.due_date = dueDate;
			if (notes.trim()) body.notes = notes.trim();
			await invoiceApi.updateInvoice(fetch, token, initial.id, /** @type {any} */ (body));
			goto(resolve('/app/invoices/[id]', { id: initial.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Edit {initial.invoice_number ?? 'draft'} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/invoices')} class="hover:text-indigo-600">Invoices</a>
		</li>
		<li aria-hidden="true">/</li>
		<li>
			<a href={resolve('/app/invoices/[id]', { id: initial.id })} class="hover:text-indigo-600"
				>{initial.invoice_number ?? 'Draft'}</a
			>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">Edit</li>
	</ol>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">Edit invoice</h1>
<p class="mt-1 text-sm text-slate-500">Issued invoices can no longer be edited.</p>

{#if err}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{err}
	</p>
{/if}

<form
	class="mt-6 max-w-4xl space-y-6"
	onsubmit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<section class="space-y-4">
		<div class="grid gap-4 sm:grid-cols-3">
			<div>
				<label for="i-project" class="block text-sm font-medium text-slate-700">Project</label>
				<input
					id="i-project"
					type="text"
					value={data.project ? data.project.name : 'Internal invoice'}
					disabled
					class="mt-1 block w-full cursor-not-allowed rounded-md border-slate-300 bg-slate-50 text-sm text-slate-600 shadow-sm"
				/>
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
		class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
		aria-labelledby="line-items-h"
	>
		<div class="flex items-center justify-between">
			<h2 id="line-items-h" class="text-base font-semibold text-slate-900">Line items *</h2>
			<button
				type="button"
				onclick={addRow}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Add line item
			</button>
		</div>
		<p class="mt-1 text-sm text-slate-500">
			Pick a project service to bill at its attached price, or add a custom line.
		</p>

		<div class="mt-4 space-y-3">
			{#each rows as row (row.key)}
				{@const amount = row.quantity * (Number(row.unit_price) || 0)}
				<div class="rounded-md border border-slate-200 bg-slate-50 p-3">
					<div class="grid gap-3 sm:grid-cols-12 sm:items-end">
						<div class="sm:col-span-2">
							<label for={`li-date-${row.key}`} class="block text-xs font-medium text-slate-600"
								>Date</label
							>
							<input
								id={`li-date-${row.key}`}
								type="date"
								bind:value={row.entry_date}
								class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>
						<div class="sm:col-span-2">
							<label for={`li-kind-${row.key}`} class="block text-xs font-medium text-slate-600"
								>Type</label
							>
							<select
								id={`li-kind-${row.key}`}
								bind:value={row.kind}
								class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
							>
								{#if data.project}
									<option value="service">Project service</option>
								{/if}
								<option value="custom">Custom</option>
							</select>
						</div>
						{#if row.kind === 'service'}
							<div class="sm:col-span-3">
								<label
									for={`li-service-${row.key}`}
									class="block text-xs font-medium text-slate-600">Service *</label
								>
								<select
									id={`li-service-${row.key}`}
									value={row.project_service_id}
									onchange={(e) =>
										onRowServiceChange(
											row,
											/** @type {HTMLSelectElement} */ (e.currentTarget).value
										)}
									class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
								>
									<option value="" disabled>Select a service</option>
									{#each projectServices as ps (ps.id)}
										<option value={ps.id}>{ps.service_name}</option>
									{/each}
								</select>
							</div>
							<div class="sm:col-span-2">
								<p class="block text-xs font-medium text-slate-600">Unit price</p>
								<p class="mt-1.5 text-sm text-slate-700">
									{row.unit_price === '' ? '—' : fmtPrice(row.unit_price)}
								</p>
							</div>
						{:else}
							<div class="sm:col-span-3">
								<label for={`li-desc-${row.key}`} class="block text-xs font-medium text-slate-600"
									>Description *</label
								>
								<input
									id={`li-desc-${row.key}`}
									type="text"
									bind:value={row.description}
									placeholder="e.g. Setup &amp; onboarding"
									class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
								/>
							</div>
							<div class="sm:col-span-2">
								<label for={`li-price-${row.key}`} class="block text-xs font-medium text-slate-600"
									>Unit price *</label
								>
								<input
									id={`li-price-${row.key}`}
									type="number"
									min="0"
									step="0.01"
									bind:value={row.unit_price}
									placeholder="0.00"
									class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
								/>
							</div>
						{/if}
						<div class="sm:col-span-1">
							<label for={`li-qty-${row.key}`} class="block text-xs font-medium text-slate-600"
								>Qty</label
							>
							<input
								id={`li-qty-${row.key}`}
								type="number"
								min="1"
								step="1"
								bind:value={row.quantity}
								class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>
						<div class="sm:col-span-1">
							<p class="block text-xs font-medium text-slate-600">Amount</p>
							<p class="mt-1.5 text-sm whitespace-nowrap text-slate-700">{fmtPrice(amount)}</p>
						</div>
						<div class="sm:col-span-1">
							<button
								type="button"
								onclick={() => removeRow(row.key)}
								class="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-100 hover:text-red-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
							>
								Remove
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
			<div class="flex justify-between">
				<dt class="text-slate-500">Tax</dt>
				<dd class="font-medium text-slate-900">{fmtPrice(0)}</dd>
			</div>
			<div class="flex justify-between border-t border-slate-200 pt-2">
				<dt class="font-medium text-slate-700">Total</dt>
				<dd class="font-semibold text-slate-900">{fmtPrice(subtotal)}</dd>
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
			Save changes
		</button>
		<a
			href={resolve('/app/invoices/[id]', { id: initial.id })}
			class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Cancel
		</a>
	</div>
</form>
