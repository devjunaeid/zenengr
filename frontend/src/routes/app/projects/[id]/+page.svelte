<script>
	import { invalidateAll } from '$app/navigation';
	import { Dialog } from 'bits-ui';
	import { resolve } from '$app/paths';
	import { SvelteMap } from 'svelte/reactivity';
	import { ApiError } from '$lib/api/client.js';
	import * as projectApi from '$lib/api/projects.js';
	import * as serviceApi from '$lib/api/services.js';
	import AssigneePicker from '$lib/components/AssigneePicker.svelte';
	import MilestoneStatusSelector from '$lib/components/MilestoneStatusSelector.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, formatDateTime, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);

	let canManage = $derived(auth.user?.role === 'admin' || auth.user?.role === 'manager');
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

	// ---- add service modal (TODO-069) ----
	let addOpen = $state(false);
	let addBusy = $state(false);
	/** @type {string|null} */
	let addErr = $state(null);
	/** @type {string[]} */
	let addSelected = $state([]);
	let addPreviewOpen = $state(false);

	/** @type {Array<{ id: string, name: string, step_count: number, description: string|null, default_price: string|null }>} */
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
	 * @param {string} id
	 */
	function toggleAddService(id) {
		if (addSelected.includes(id)) {
			addSelected = addSelected.filter((x) => x !== id);
		} else {
			addSelected = [...addSelected, id];
		}
	}

	async function confirmAdd() {
		if (addSelected.length === 0) {
			addErr = 'Pick at least one service.';
			return;
		}
		addBusy = true;
		addErr = null;
		try {
			for (const sid of addSelected) {
				await projectApi.attachService(fetch, token, data.project.id, { service_id: sid });
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
	 * @param {string|null|undefined} v
	 */
	function fmtPrice(v) {
		if (v == null || v === '') return '—';
		const n = Number(v);
		if (Number.isNaN(n)) return '—';
		return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
	}

	/**
	 * @param {string|null|undefined} d
	 */
	function fmtDate(d) {
		return d ? formatDate(d) : '—';
	}

	const projectStatusOptions = ['draft', 'active', 'on_hold', 'completed', 'cancelled'];
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

	<div
		class="mt-5 rounded-md border border-dashed border-slate-300 bg-slate-50 p-4"
		aria-label="Linked invoices"
	>
		<div class="flex items-center justify-between">
			<p class="text-sm font-medium text-slate-700">Linked invoices</p>
			<StatusBadge status="draft" />
		</div>
		<p class="mt-1 text-xs text-slate-500">Invoicing coming soon.</p>
	</div>

	<div class="mt-5 grid gap-3 text-xs text-slate-500 sm:grid-cols-2">
		<p>Created {formatDateTime(data.project.created_at)}</p>
		<p>Updated {formatDateTime(data.project.updated_at)}</p>
	</div>
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
										disabled={!canManage || isCancelled}
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
										disabled={!canManage || isCancelled}
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
						<li>
							<label
								class="flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 hover:bg-slate-100"
							>
								<input
									type="checkbox"
									{checked}
									onchange={() => toggleAddService(svc.id)}
									class="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
								<span class="flex-1">
									<span class="block text-sm font-medium text-slate-900">{svc.name}</span>
									<span class="mt-0.5 block text-xs text-slate-500">
										{svc.step_count}
										{svc.step_count === 1 ? 'step' : 'steps'}
										{#if svc.default_price}· default {fmtPrice(svc.default_price)}{/if}
									</span>
									{#if svc.description}
										<span class="mt-1 block text-xs text-slate-600">{svc.description}</span>
									{/if}
								</span>
							</label>
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
