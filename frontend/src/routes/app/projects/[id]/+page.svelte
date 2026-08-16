<script>
	import { invalidateAll } from '$app/navigation';
	import { Dialog } from 'bits-ui';
	import { resolve } from '$app/paths';
	import { SvelteMap } from 'svelte/reactivity';
	import { ApiError } from '$lib/api/client.js';
	import * as projectApi from '$lib/api/projects.js';
	import * as serviceApi from '$lib/api/services.js';
	import AssigneePicker from '$lib/components/AssigneePicker.svelte';
	import CommentThread from '$lib/components/CommentThread.svelte';
	import MilestoneStatusSelector from '$lib/components/MilestoneStatusSelector.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import ToggleSwitch from '$lib/components/ToggleSwitch.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, formatDateTime, fmtPrice, humanize } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import arrowDown from '@iconify-icons/mdi/arrow-down';
	import arrowUp from '@iconify-icons/mdi/arrow-up';
	import minusCircle from '@iconify-icons/mdi/minus-circle';
	import plusCircle from '@iconify-icons/mdi/plus-circle';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);

	let canManage = $derived(auth.can('manage', 'projects'));
	let canManageMilestones = $derived(auth.can('manage', 'milestones'));
	let isEmployee = $derived(auth.user?.role === 'employee');

	// ---- status + errors ----
	/** @type {string|null} */
	let actionErr = $state(null);
	/** @type {string|null} */
	let actionMsg = $state(null);
	let statusBusy = $state(false);

	async function changeStatus(/** @type {string} */ next) {
		statusBusy = true;
		actionErr = null;
		actionMsg = null;
		try {
			await projectApi.updateProject(fetch, token, data.project.id, { status: next });
			actionMsg = `Status changed to ${humanize(next)}.`;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Status change failed.';
		} finally {
			statusBusy = false;
		}
	}

	// ---- auto-invoice toggle ----
	let autoInvoiceBusy = $state(false);

	/**
	 * @param {boolean} next
	 */
	async function toggleAutoInvoice(next) {
		autoInvoiceBusy = true;
		actionErr = null;
		actionMsg = null;
		try {
			await projectApi.updateProject(fetch, token, data.project.id, { auto_invoice: next });
			actionMsg = `Auto-invoice ${next ? 'enabled' : 'disabled'}.`;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not update auto-invoice.';
		} finally {
			autoInvoiceBusy = false;
		}
	}

	// ---- add service modal (TODO-069) ----
	let addOpen = $state(false);
	let addBusy = $state(false);
	/** @type {string|null} */
	let addErr = $state(null);
	/** @type {string[]} */
	let addSelected = $state([]);
	/** @type {Record<string, number|string>} */
	let addPrices = $state({});
	let addPreviewOpen = $state(false);

	/** @type {import('$lib/api/services.js').ServiceListItem[]} */
	let allServices = $state([]);
	/** @type {Record<string, import('$lib/api/services.js').MilestoneStep[]|null>} */
	let allServiceDetails = $state({});
	let servicesLoading = $state(false);

	let availableToAttach = $derived(
		allServices.filter(
			(s) => !data.project.services.some((ps) => ps.service_id === s.id && ps.status === 'active')
		)
	);

	async function openAddModal() {
		addOpen = true;
		addErr = null;
		addSelected = [];
		addPrices = {};
		addPreviewOpen = false;
		if (allServices.length === 0) {
			servicesLoading = true;
			try {
				const res = await serviceApi.listServices(fetch, token, {
					page_size: 100,
					is_active: true
				});
				allServices = res.items;
			} catch (e) {
				addErr = e instanceof ApiError ? e.message : 'Could not load services.';
			} finally {
				servicesLoading = false;
			}
		}
	}

	$effect(() => {
		if (addOpen && addPreviewOpen && addSelected.length > 0) {
			loadAddPreview();
		}
	});

	async function loadAddPreview() {
		const missing = addSelected.filter((id) => allServiceDetails[id] === undefined);
		if (missing.length === 0) return;
		try {
			const details = await Promise.all(
				missing.map((id) => serviceApi.getService(fetch, token, id))
			);
			const next = { ...allServiceDetails };
			for (const d of details) {
				next[d.id] = (d.steps ?? []).slice().sort((a, b) => a.sequence_order - b.sequence_order);
			}
			allServiceDetails = next;
		} catch (e) {
			addErr = e instanceof ApiError ? e.message : 'Could not load milestone preview.';
		}
	}

	/**
	 * @param {import('$lib/api/services.js').ServiceListItem} svc
	 */
	function toggleAddService(svc) {
		if (addSelected.includes(svc.id)) {
			addSelected = addSelected.filter((x) => x !== svc.id);
			const next = { ...addPrices };
			delete next[svc.id];
			addPrices = next;
		} else {
			addSelected = [...addSelected, svc.id];
			addPrices = { ...addPrices, [svc.id]: svc.default_price ?? '' };
		}
	}

	/**
	 * Inline price validation: empty means "use default", otherwise must be > 0.
	 * @param {string} id
	 * @returns {string|null}
	 */
	function addPriceError(id) {
		const v = addPrices[id];
		if (v === undefined || v === null || v === '') return null;
		const n = Number(v);
		if (!Number.isFinite(n) || n <= 0) return 'Price must be greater than 0.';
		return null;
	}

	async function confirmAdd() {
		if (addSelected.length === 0) {
			addErr = 'Pick at least one service.';
			return;
		}
		for (const sid of addSelected) {
			if (addPriceError(sid)) {
				addErr = 'Enter a valid price (greater than 0) or clear it to use the default.';
				return;
			}
		}
		addBusy = true;
		addErr = null;
		try {
			for (const sid of addSelected) {
				/** @type {{ service_id: string, price?: number|string }} */
				const body = { service_id: sid };
				const price = addPrices[sid];
				if (price !== undefined && price !== null && price !== '') body.price = price;
				await projectApi.attachService(fetch, token, data.project.id, body);
			}
			addOpen = false;
			await invalidateAll();
		} catch (e) {
			addErr = e instanceof ApiError ? e.message : 'Could not add service.';
		} finally {
			addBusy = false;
		}
	}

	// ---- milestone update handlers ----
	/** @type {Record<string, boolean>} */
	let milestoneBusy = $state({});

	/**
	 * @param {import('$lib/api/projects.js').ProjectMilestoneItem} m
	 * @param {Record<string, any>} patch
	 */
	async function patchMilestone(m, patch) {
		milestoneBusy = { ...milestoneBusy, [m.id]: true };
		actionErr = null;
		actionMsg = null;
		try {
			await projectApi.updateMilestone(fetch, token, data.project.id, m.id, patch);
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Update failed.';
		} finally {
			const next = { ...milestoneBusy };
			delete next[m.id];
			milestoneBusy = next;
		}
	}

	// ---- derived ----
	let milestoneTotal = $derived(data.project.milestones.length);
	let milestoneCompleted = $derived(
		data.project.milestones.filter((m) => m.status === 'completed').length
	);
	let progressPct = $derived(
		milestoneTotal === 0
			? 0
			: Math.min(100, Math.round((milestoneCompleted / milestoneTotal) * 100))
	);

	/**
	 * Milestones grouped by project_service_id.
	 * @type {Array<{ key: string, projectService: import('$lib/api/projects.js').ProjectServiceItem, items: import('$lib/api/projects.js').ProjectMilestoneItem[] }>}
	 */
	let milestonesByService = $derived.by(() => {
		const map = new SvelteMap();
		for (const m of data.project.milestones) {
			const arr = map.get(m.project_service_id) ?? [];
			arr.push(m);
			map.set(m.project_service_id, arr);
		}
		const out = [];
		for (const ps of data.project.services) {
			const items = (map.get(ps.id) ?? [])
				.slice()
				.sort(
					(
						/** @type {import('$lib/api/projects.js').ProjectMilestoneItem} */ a,
						/** @type {import('$lib/api/projects.js').ProjectMilestoneItem} */ b
					) => a.sequence_order - b.sequence_order
				);
			out.push({ key: ps.id, projectService: ps, items });
		}
		return out;
	});

	/**
	 * @param {string|null|undefined} d
	 */
	function fmtDate(d) {
		return d ? formatDate(d) : '—';
	}

	const projectStatusOptions = ['draft', 'active', 'on_hold', 'completed', 'cancelled'];

	// ---- ledger (FEAT-018) ----
	/** @type {import('$lib/api/projects.js').LedgerResponse|null} */
	let ledgerData = $derived(data.ledger);
	/** @type {import('$lib/api/projects.js').LedgerEntry[]} */
	let ledgerEntries = $derived(
		(ledgerData?.entries ?? []).slice().sort((a, b) => {
			const da = a.entry_date ?? a.created_at;
			const db = b.entry_date ?? b.created_at;
			return da < db ? -1 : da > db ? 1 : 0;
		})
	);
	/** @type {import('$lib/api/projects.js').LedgerSummary|null} */
	let ledgerSummary = $derived(ledgerData?.summary ?? null);

	/**
	 * Icon + color per ledger entry: payment = money in, refund = money out,
	 * negative charge = reversal.
	 * @param {import('$lib/api/projects.js').LedgerEntry} e
	 */
	function entryMeta(e) {
		const n = Number(e.amount) || 0;
		if (e.type === 'payment') {
			return { icon: arrowDown, text: 'text-green-700', bg: 'bg-green-100' };
		}
		if (e.type === 'refund' || n < 0) {
			return {
				icon: e.type === 'refund' ? arrowUp : minusCircle,
				text: 'text-red-600',
				bg: 'bg-red-100'
			};
		}
		return { icon: plusCircle, text: 'text-slate-600', bg: 'bg-indigo-100' };
	}

	/**
	 * Signed price: payments get "+", refunds/reversals get "−", plain
	 * charges render as their positive amount.
	 * @param {import('$lib/api/projects.js').LedgerEntry} e
	 */
	function entryPrice(e) {
		const n = Number(e.amount) || 0;
		const abs = fmtPrice(Math.abs(n));
		if (abs === '—') return '—';
		if (e.type === 'payment') return `+${abs}`;
		if (e.type === 'refund' || n < 0) return `−${abs}`;
		return fmtPrice(n);
	}

	/** @param {import('$lib/api/projects.js').LedgerEntry} e */
	function entryLabel(e) {
		if (e.description) return e.description;
		if (e.source_type === 'manual_adjustment') return 'Manual adjustment';
		return humanize(e.type);
	}

	/** @param {import('$lib/api/projects.js').LedgerEntry} e */
	function entrySubtext(e) {
		if (e.source_type === 'manual_adjustment') return 'Manual adjustment';
		if (e.source_type === 'transaction') return 'Payment';
		return 'Charge';
	}

	// ---- add adjustment dialog ----
	let adjustOpen = $state(false);
	let adjustBusy = $state(false);
	/** @type {string|null} */
	let adjustErr = $state(null);
	/** @type {number|string} */
	let adjustAmount = $state('');
	/** @type {string} */
	let adjustDescription = $state('');

	function openAdjustDialog() {
		adjustErr = null;
		adjustAmount = '';
		adjustDescription = '';
		adjustOpen = true;
	}

	async function saveAdjustment() {
		adjustErr = null;
		const n = Number(adjustAmount);
		if (adjustAmount === '' || !Number.isFinite(n) || n === 0) {
			adjustErr = 'Enter a non-zero signed amount (negative reduces the total).';
			return;
		}
		if (!adjustDescription.trim()) {
			adjustErr = 'Add a description.';
			return;
		}
		adjustBusy = true;
		try {
			await projectApi.addLedgerAdjustment(fetch, token, data.project.id, {
				amount: String(n),
				description: adjustDescription.trim()
			});
			adjustOpen = false;
			await invalidateAll();
		} catch (e) {
			adjustErr = e instanceof ApiError ? e.message : 'Could not add adjustment.';
		} finally {
			adjustBusy = false;
		}
	}

	// ---- edit discount dialog ----
	let discountOpen = $state(false);
	let discountBusy = $state(false);
	/** @type {string|null} */
	let discountErr = $state(null);
	/** @type {''|'percentage'|'fixed'} */
	let discountType = $state('');
	/** @type {number|string} */
	let discountValue = $state('');

	function openDiscountDialog() {
		discountErr = null;
		discountType = ledgerSummary?.discount_type ?? '';
		discountValue = ledgerSummary?.discount_value != null ? ledgerSummary.discount_value : '';
		discountOpen = true;
	}

	async function saveDiscount() {
		discountErr = null;
		/** @type {{ discount_type: 'percentage'|'fixed'|null, discount_value: number|null }} */
		const body = { discount_type: null, discount_value: null };
		if (discountType === 'percentage' || discountType === 'fixed') {
			const v = Number(discountValue);
			if (discountValue === '' || !Number.isFinite(v) || v < 0) {
				discountErr = 'Enter a value of 0 or more.';
				return;
			}
			if (discountType === 'percentage' && v > 100) {
				discountErr = 'Percentage must be 100 or less.';
				return;
			}
			body.discount_type = discountType;
			body.discount_value = v;
		}
		discountBusy = true;
		try {
			await projectApi.setProjectDiscount(fetch, token, data.project.id, body);
			discountOpen = false;
			await invalidateAll();
		} catch (e) {
			discountErr = e instanceof ApiError ? e.message : 'Could not save discount.';
		} finally {
			discountBusy = false;
		}
	}

	/**
	 * Summary row for the discount: "-X" with a type hint, or "—" when none.
	 * @returns {{ display: string, hint: string|null }}
	 */
	function discountDisplay() {
		const s = ledgerSummary;
		if (!s?.discount_type) return { display: '—', hint: null };
		const amount = Number(s.discount_amount) || 0;
		const abs = fmtPrice(Math.abs(amount));
		const display = abs === '—' ? '—' : `−${abs}`;
		const hint =
			s.discount_type === 'percentage'
				? `${Math.round((Number(s.discount_value) || 0) * 100) / 100}%`
				: 'fixed';
		return { display, hint };
	}
</script>

<svelte:head><title>{data.project.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/projects')} class="hover:text-indigo-600">Projects</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">{data.project.name}</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div class="flex items-center gap-3">
		<h1 class="text-2xl font-semibold text-slate-900">{data.project.name}</h1>
		<StatusBadge status={data.project.status} />
	</div>
	{#if canManage}
		<div class="flex flex-wrap items-center gap-2">
			<span
				class="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5"
			>
				<ToggleSwitch
					checked={data.project.auto_invoice}
					disabled={autoInvoiceBusy}
					onchange={toggleAutoInvoice}
					label="Auto-invoice"
				/>
				<span class="text-sm font-medium text-slate-700">Auto-invoice</span>
			</span>
			<a
				href={resolve('/app/projects/[id]/edit', { id: data.project.id })}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Edit
			</a>
			<label for="status-select" class="sr-only">Change status</label>
			<select
				id="status-select"
				value={data.project.status}
				disabled={statusBusy}
				aria-busy={statusBusy}
				onchange={(e) => changeStatus(/** @type {HTMLSelectElement} */ (e.currentTarget).value)}
				class="rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#each projectStatusOptions as opt (opt)}
					<option value={opt}>{humanize(opt)}</option>
				{/each}
			</select>
			<button
				type="button"
				disabled
				title="Project deletion is not yet supported in MVP"
				class="cursor-not-allowed rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-400"
			>
				Delete
			</button>
		</div>
	{/if}
</div>

{#if data.project.auto_invoice}
	<p class="mt-2 text-sm text-slate-500">Open draft invoice is auto-updated with new services.</p>
{/if}

{#if isEmployee}
	<p
		role="status"
		class="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
	>
		View only — contact an admin to make changes.
	</p>
{/if}

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

<!-- Overview card (TODO-073) -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="overview-h"
>
	<h2 id="overview-h" class="text-base font-semibold text-slate-900">Overview</h2>
	<dl class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Client</dt>
			<dd class="mt-1 text-sm">
				<a
					href={resolve('/app/clients/[id]', { id: data.project.client_id })}
					class="text-indigo-600 hover:text-indigo-500"
				>
					View client
				</a>
			</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Start date</dt>
			<dd class="mt-1 text-sm text-slate-900">{fmtDate(data.project.start_date)}</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Owner</dt>
			<dd class="mt-1 text-sm text-slate-900">
				{#if data.project.owner_id}
					{data.users.find((u) => u.id === data.project.owner_id)?.full_name ?? '—'}
				{:else}
					<span class="text-slate-400">Unassigned</span>
				{/if}
			</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Services</dt>
			<dd class="mt-1 text-sm text-slate-900">{data.project.services.length}</dd>
		</div>
	</dl>

	<div class="mt-5">
		<div class="flex items-baseline justify-between">
			<p class="text-xs font-medium tracking-wide text-slate-500 uppercase">Milestone progress</p>
			<p class="text-xs text-slate-600">
				{milestoneCompleted} / {milestoneTotal}
				{#if milestoneTotal > 0}({progressPct}%){/if}
			</p>
		</div>
		{#if milestoneTotal > 0}
			<div
				class="mt-2 h-2 w-full rounded-full bg-slate-100"
				role="progressbar"
				aria-valuenow={milestoneCompleted}
				aria-valuemin={0}
				aria-valuemax={milestoneTotal}
				aria-label={`Milestone progress for ${data.project.name}`}
			>
				<div class="h-2 rounded-full bg-indigo-600" style="width: {progressPct}%"></div>
			</div>
		{:else}
			<p class="mt-2 text-sm text-slate-500">No milestones yet.</p>
		{/if}
	</div>

	<div class="mt-5 grid gap-4 sm:grid-cols-3">
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total invoiced</dt>
			<dd class="mt-1 text-lg font-semibold text-slate-900">
				{data.overview ? fmtPrice(data.overview.total_invoiced) : '—'}
			</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total paid</dt>
			<dd class="mt-1 text-lg font-semibold text-slate-900">
				{data.overview ? fmtPrice(data.overview.total_paid) : '—'}
			</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Balance due</dt>
			<dd class="mt-1 text-lg font-semibold text-slate-900">
				{data.overview ? fmtPrice(data.overview.balance_due) : '—'}
			</dd>
		</div>
	</div>

	{#if data.overview?.service_breakdown?.length}
		<div class="mt-5 overflow-hidden rounded-md border border-slate-200">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-100">
					<tr>
						<th
							scope="col"
							class="px-4 py-2.5 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Service</th
						>
						<th
							scope="col"
							class="px-4 py-2.5 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Invoiced</th
						>
						<th
							scope="col"
							class="px-4 py-2.5 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Paid</th
						>
						<th
							scope="col"
							class="px-4 py-2.5 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Outstanding</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.overview.service_breakdown as row (row.service_id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-2.5 text-sm font-medium text-slate-900">{row.service_name}</td>
							<td class="px-4 py-2.5 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(row.total_invoiced)}</td
							>
							<td class="px-4 py-2.5 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(row.total_paid)}</td
							>
							<td class="px-4 py-2.5 text-right text-sm whitespace-nowrap text-slate-900"
								>{fmtPrice(row.total_outstanding)}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	<div class="mt-5">
		<div class="flex items-center justify-between">
			<p class="text-sm font-medium text-slate-700">Linked invoices</p>
			<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
			<a
				href={`${resolve('/app/invoices/new')}?project_id=${data.project.id}`}
				class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
			>
				New invoice
			</a>
			<!-- eslint-enable svelte/no-navigation-without-resolve -->
		</div>
		{#if !data.overview}
			<p class="mt-2 text-sm text-slate-500">Could not load invoice summary.</p>
		{:else if data.overview.linked_invoices.length === 0}
			<p class="mt-2 text-sm text-slate-500">No invoices yet.</p>
		{:else}
			<ul class="mt-3 divide-y divide-slate-200 rounded-md border border-slate-200">
				{#each data.overview.linked_invoices as inv (inv.id)}
					<li class="flex items-center justify-between gap-3 px-4 py-3">
						<a
							href={resolve('/app/invoices/[id]', { id: inv.id })}
							class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
						>
							{inv.number ?? 'Draft'}
						</a>
						<div class="flex items-center gap-3">
							<StatusBadge status={inv.status} />
							<span class="text-sm whitespace-nowrap text-slate-700">{fmtPrice(inv.total)}</span>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<div class="mt-5 grid gap-3 text-xs text-slate-500 sm:grid-cols-2">
		<p>Created {formatDateTime(data.project.created_at)}</p>
		<p>Updated {formatDateTime(data.project.updated_at)}</p>
	</div>
</section>

<!-- Ledger section (FEAT-018) -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="ledger-h"
>
	<div
		class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4"
	>
		<div>
			<h2 id="ledger-h" class="text-base font-semibold text-slate-900">Ledger</h2>
			<p class="mt-0.5 text-sm text-slate-500">
				Balance-forward timeline of charges, payments and refunds.
			</p>
		</div>
		{#if canManage}
			<div class="flex flex-wrap items-center gap-2">
				<button
					type="button"
					onclick={openAdjustDialog}
					class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Add adjustment
				</button>
				<button
					type="button"
					onclick={openDiscountDialog}
					class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Edit discount
				</button>
			</div>
		{/if}
	</div>

	{#if !ledgerData}
		<p class="px-6 py-8 text-sm text-slate-500">Ledger unavailable.</p>
	{:else if ledgerEntries.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No ledger entries yet.</p>
	{:else}
		<ul class="divide-y divide-slate-100">
			{#each ledgerEntries as e (e.id)}
				{@const meta = entryMeta(e)}
				{@const price = entryPrice(e)}
				<li class="flex items-center gap-3 px-6 py-3">
					<span
						class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full {meta.bg}"
						aria-hidden="true"
					>
						<Icon icon={meta.icon} class="h-4 w-4 {meta.text}" />
					</span>
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-slate-900" title={entryLabel(e)}>
							{entryLabel(e)}
						</p>
						<p class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500">
							<span>{entrySubtext(e)}</span>
							<span aria-hidden="true">·</span>
							<span>{e.entry_date ? formatDate(e.entry_date) : formatDateTime(e.created_at)}</span>
							{#if e.type === 'charge' && e.invoice_ref && e.invoice_number}
								<a
									href={resolve('/app/invoices/[id]', { id: e.invoice_ref })}
									class="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700 ring-1 ring-indigo-600/20 hover:bg-indigo-100"
								>
									Included in {e.invoice_number}
								</a>
							{/if}
						</p>
					</div>
					<p class="shrink-0 text-sm font-semibold whitespace-nowrap {meta.text}">{price}</p>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<!-- Project ledger balance summary (FEAT-018) -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="ledger-balance-h"
>
	<h2 id="ledger-balance-h" class="text-base font-semibold text-slate-900">
		Project ledger (balance)
	</h2>
	{#if !ledgerData}
		<p class="mt-4 text-sm text-slate-500">Ledger unavailable.</p>
	{:else}
		{@const disc = discountDisplay()}
		{@const due = Number(ledgerSummary?.due) || 0}
		<dl class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Subtotal</dt>
				<dd class="mt-1 text-lg font-semibold text-slate-900">
					{fmtPrice(ledgerSummary?.subtotal)}
				</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Discount</dt>
				<dd class="mt-1 text-lg font-semibold text-slate-900">
					{disc.display}
					{#if disc.hint}
						<span class="ml-1 text-xs font-normal text-slate-500">({disc.hint})</span>
					{/if}
				</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total</dt>
				<dd class="mt-1 text-lg font-semibold text-slate-900">{fmtPrice(ledgerSummary?.total)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Paid</dt>
				<dd class="mt-1 text-lg font-semibold text-green-700">{fmtPrice(ledgerSummary?.paid)}</dd>
			</div>
			<div>
				<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Due</dt>
				<dd class="mt-1 text-lg font-bold {due > 0 ? 'text-red-600' : 'text-green-700'}">
					{fmtPrice(ledgerSummary?.due)}
				</dd>
			</div>
		</dl>
	{/if}
</section>

<!-- Services section (TODO-071) -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="services-h"
>
	<div class="flex items-center justify-between border-b border-slate-200 px-6 py-4">
		<div>
			<h2 id="services-h" class="text-base font-semibold text-slate-900">Services</h2>
			<p class="mt-0.5 text-sm text-slate-500">
				{data.project.services.length}
				{data.project.services.length === 1 ? 'service' : 'services'} attached
			</p>
		</div>
		{#if canManage}
			<button
				type="button"
				onclick={openAddModal}
				class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Add service
			</button>
		{/if}
	</div>

	{#if data.project.services.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No services attached yet.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Service</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Price</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Milestones</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.project.services as ps (ps.id)}
						{@const isCancelled = ps.status === 'cancelled'}
						<tr class={isCancelled ? 'bg-slate-50 text-slate-500' : 'hover:bg-slate-50'}>
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<span class={isCancelled ? 'line-through' : ''}>{ps.service_name}</span>
							</td>
							<td class="px-4 py-3"><StatusBadge status={ps.status} /></td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(ps.price_at_attachment)}</td
							>
							<td class="px-4 py-3 text-right text-sm text-slate-700">
								{data.project.milestones.filter((m) => m.project_service_id === ps.id).length}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<!-- Milestones section -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="milestones-h"
>
	<h2 id="milestones-h" class="text-base font-semibold text-slate-900">Milestones</h2>
	{#if data.project.milestones.length === 0}
		<p class="mt-4 text-sm text-slate-500">No milestones yet.</p>
	{:else}
		<div class="mt-4 space-y-6">
			{#each milestonesByService as group (group.key)}
				{@const isCancelled = group.projectService.status === 'cancelled'}
				<div>
					<div class="flex items-center gap-2">
						<h3
							class="text-sm font-semibold {isCancelled
								? 'text-slate-500 line-through'
								: 'text-slate-900'}"
						>
							{group.projectService.service_name}
						</h3>
						<StatusBadge status={group.projectService.status} />
						<span class="text-xs text-slate-500">
							· {group.items.length}
							{group.items.length === 1 ? 'milestone' : 'milestones'}
						</span>
					</div>

					<ul class="mt-3 divide-y divide-slate-200 rounded-md border border-slate-200">
						{#each group.items as m (m.id)}
							{@const mBusy = Boolean(milestoneBusy[m.id])}
							<li
								class="grid gap-2 px-4 py-3 sm:grid-cols-12 sm:items-center {isCancelled
									? 'bg-slate-50 text-slate-500'
									: ''}"
							>
								<div class="sm:col-span-5">
									<div class="flex items-start gap-2">
										<span
											class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
											aria-hidden="true"
										>
											{m.sequence_order}
										</span>
										<div class="min-w-0">
											<p
												class="text-sm font-medium {isCancelled
													? 'line-through'
													: 'text-slate-900'}"
											>
												{m.name}
											</p>
											{#if m.description}
												<p class="mt-0.5 text-xs text-slate-500">{m.description}</p>
											{/if}
										</div>
									</div>
								</div>
								<div class="sm:col-span-3">
									<MilestoneStatusSelector
										value={m.status}
										busy={mBusy}
										disabled={!canManageMilestones || isCancelled}
										onchange={(next) => patchMilestone(m, { status: next })}
										id={`m-status-${m.id}`}
									/>
								</div>
								<div class="text-xs text-slate-600 sm:col-span-2">
									<p>
										<span class="block text-slate-500">Planned</span>
										{fmtDate(m.planned_date)}
									</p>
									<p class="mt-1">
										<span class="block text-slate-500">Actual</span>
										{fmtDate(m.actual_date)}
									</p>
								</div>
								<div class="sm:col-span-2">
									<AssigneePicker
										value={m.assignee_id}
										users={data.users}
										busy={mBusy}
										disabled={!canManageMilestones || isCancelled}
										onchange={(uid) => patchMilestone(m, { assignee_id: uid })}
										id={`m-assignee-${m.id}`}
									/>
								</div>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
	{/if}
</section>

<!-- Comments section (TODO-101/102) -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="comments-h"
>
	<h2 id="comments-h" class="text-base font-semibold text-slate-900">Comments</h2>
	<div class="mt-2">
		<CommentThread projectId={data.project.id} {fetch} {token} realm="admin" staff={true} />
	</div>
</section>

<!-- Add adjustment dialog (FEAT-018) -->
<Dialog.Root bind:open={adjustOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Add adjustment</Dialog.Title>
				<Dialog.Close
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
				Signed amount: positive adds to the project total, negative offsets it. The change is
				appended to the ledger and cannot be edited or removed.
			</Dialog.Description>

			{#if adjustErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{adjustErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					saveAdjustment();
				}}
			>
				<div>
					<label for="adjust-amount" class="block text-sm font-medium text-slate-700">Amount</label>
					<input
						id="adjust-amount"
						type="number"
						step="0.01"
						placeholder="0.00"
						bind:value={adjustAmount}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="adjust-desc" class="block text-sm font-medium text-slate-700"
						>Description</label
					>
					<input
						id="adjust-desc"
						type="text"
						placeholder="e.g. Service cancellation credit"
						bind:value={adjustDescription}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div class="flex justify-end gap-3 pt-2">
					<Dialog.Close
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={adjustBusy}
						aria-busy={adjustBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if adjustBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Add adjustment
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Edit discount dialog (FEAT-018) -->
<Dialog.Root bind:open={discountOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Edit discount</Dialog.Title>
				<Dialog.Close
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
				Single active discount — a new value replaces the current one. It feeds the ledger balance
				and is auto-applied to new invoices.
			</Dialog.Description>

			{#if discountErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{discountErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					saveDiscount();
				}}
			>
				<div>
					<label for="discount-type" class="block text-sm font-medium text-slate-700">Type</label>
					<select
						id="discount-type"
						bind:value={discountType}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					>
						<option value="">None</option>
						<option value="percentage">Percentage</option>
						<option value="fixed">Fixed amount</option>
					</select>
				</div>
				<div>
					<label for="discount-value" class="block text-sm font-medium text-slate-700">Value</label>
					<input
						id="discount-value"
						type="number"
						min="0"
						step={discountType === 'percentage' ? '1' : '0.01'}
						placeholder={discountType === 'percentage' ? '10' : '0.00'}
						disabled={discountType === ''}
						bind:value={discountValue}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
					/>
					{#if discountType === 'percentage'}
						<p class="mt-1 text-xs text-slate-500">Percent of the ledger subtotal.</p>
					{:else if discountType === 'fixed'}
						<p class="mt-1 text-xs text-slate-500">Flat amount off the ledger subtotal.</p>
					{/if}
				</div>
				<div class="flex justify-end gap-3 pt-2">
					<Dialog.Close
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={discountBusy}
						aria-busy={discountBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if discountBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Save discount
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Add service modal (bits-ui Dialog) -->
<Dialog.Root bind:open={addOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Add service</Dialog.Title>
				<Dialog.Close
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
				Adding a service creates new milestones and bills via a new invoice (FR-7.6).
			</Dialog.Description>

			{#if addErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{addErr}
				</p>
			{/if}

			{#if servicesLoading}
				<div class="mt-4 flex items-center gap-2 text-sm text-slate-600">
					<Spinner class="h-4 w-4 text-indigo-600" /> Loading services…
				</div>
			{:else if availableToAttach.length === 0}
				<p class="mt-4 text-sm text-slate-500">No more services available to add.</p>
			{:else}
				<ul
					class="mt-4 max-h-72 space-y-2 overflow-y-auto"
					role="group"
					aria-label="Available services"
				>
					{#each availableToAttach as svc (svc.id)}
						{@const checked = addSelected.includes(svc.id)}
						{@const priceErr = checked ? addPriceError(svc.id) : null}
						<li>
							<div
								class="flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
							>
								<input
									id={`add-svc-${svc.id}`}
									type="checkbox"
									{checked}
									onchange={() => toggleAddService(svc)}
									class="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
								<div class="min-w-0 flex-1">
									<label for={`add-svc-${svc.id}`} class="cursor-pointer">
										<span class="block text-sm font-medium text-slate-900">{svc.name}</span>
										<span class="mt-0.5 block text-xs text-slate-500">
											{svc.step_count}
											{svc.step_count === 1 ? 'step' : 'steps'}
											{#if svc.default_price}· default {fmtPrice(svc.default_price)}{/if}
										</span>
										{#if svc.description}
											<span class="mt-1 block text-xs text-slate-600">{svc.description}</span>
										{/if}
									</label>
									{#if checked}
										<div class="mt-2 flex max-w-xs items-center gap-2">
											<label
												for={`add-price-${svc.id}`}
												class="shrink-0 text-xs font-medium text-slate-600">Price</label
											>
											<input
												id={`add-price-${svc.id}`}
												type="number"
												min="0.01"
												step="0.01"
												placeholder="Default price"
												bind:value={addPrices[svc.id]}
												class="w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
											/>
										</div>
										{#if priceErr}
											<p role="alert" class="mt-1 text-xs text-red-600">{priceErr}</p>
										{/if}
									{/if}
								</div>
							</div>
						</li>
					{/each}
				</ul>

				{#if addSelected.length > 0}
					<div class="mt-3">
						<button
							type="button"
							onclick={() => (addPreviewOpen = !addPreviewOpen)}
							aria-expanded={addPreviewOpen}
							aria-controls="add-preview-steps"
							class="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="h-4 w-4 transition-transform {addPreviewOpen ? 'rotate-90' : ''}"
								aria-hidden="true"
							>
								<path
									fill-rule="evenodd"
									d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
									clip-rule="evenodd"
								/>
							</svg>
							{addPreviewOpen ? 'Hide' : 'Preview'} milestones
						</button>
					</div>
					{#if addPreviewOpen}
						<div
							id="add-preview-steps"
							class="mt-2 max-h-40 space-y-1 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"
						>
							{#each addSelected as sid (sid)}
								{@const detail = allServiceDetails[sid]}
								{@const svc = allServices.find((s) => s.id === sid)}
								{#if detail}
									<div>
										<p class="text-xs font-semibold text-slate-700">{svc?.name ?? 'Service'}</p>
										<ol class="ml-4 list-decimal">
											{#each detail as st (st.id ?? `${st.sequence_order}`)}
												<li>
													{st.name}
													{#if st.expected_duration_days}
														<span class="text-xs text-slate-500"
															>({st.expected_duration_days}d)</span
														>
													{/if}
												</li>
											{/each}
										</ol>
									</div>
								{:else}
									<p class="text-xs text-slate-500">Loading {svc?.name ?? '…'}…</p>
								{/if}
							{/each}
						</div>
					{/if}
				{/if}
			{/if}

			<div class="mt-6 flex justify-end gap-3">
				<Dialog.Close
					class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Cancel
				</Dialog.Close>
				<button
					type="button"
					disabled={addBusy || addSelected.length === 0}
					aria-busy={addBusy}
					onclick={confirmAdd}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if addBusy}<Spinner class="h-4 w-4 text-white" />{/if}
					Add
				</button>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
