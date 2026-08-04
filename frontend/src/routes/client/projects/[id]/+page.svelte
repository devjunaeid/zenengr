<script>
	import { resolve } from '$app/paths';
	import CommentThread from '$lib/components/CommentThread.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { formatDate, fmtPrice } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (portalAuth.token);

	const project = $derived(data.project);

	const milestoneTotal = $derived(project.milestone_total);
	const milestoneCompleted = $derived(project.milestone_completed);
	const progressPct = $derived(
		milestoneTotal === 0
			? 0
			: Math.min(100, Math.round((milestoneCompleted / milestoneTotal) * 100))
	);

	// Financials are nested under `financials` in the current backend shape;
	// also tolerate a flat response just in case the API shape changes.
	const totalInvoiced = $derived(
		project.financials?.total_invoiced ?? /** @type {any} */ (project).total_invoiced
	);
	const totalPaid = $derived(
		project.financials?.total_paid ?? /** @type {any} */ (project).total_paid
	);
	const balanceDue = $derived(
		project.financials?.balance_due ?? /** @type {any} */ (project).balance_due
	);

	// The client project API returns milestones without a project_service_id,
	// so they render as one flat list ordered by sequence_order.
	const milestones = $derived(
		project.milestones.slice().sort((a, b) => a.sequence_order - b.sequence_order)
	);

	/**
	 * @param {string|null|undefined} d
	 */
	function fmtDate(d) {
		return d ? formatDate(d) : '—';
	}
</script>

<svelte:head><title>{project.name} — Client Portal</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/client/projects')} class="hover:text-indigo-600">Projects</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">{project.name}</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center gap-3">
	<h1 class="text-2xl font-semibold text-slate-900">{project.name}</h1>
	<StatusBadge status={project.status} />
</div>

<!-- Overview card -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="overview-h"
>
	<h2 id="overview-h" class="text-base font-semibold text-slate-900">Overview</h2>
	<dl class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Start date</dt>
			<dd class="mt-1 text-sm text-slate-900">{fmtDate(project.start_date)}</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Services</dt>
			<dd class="mt-1 text-sm text-slate-900">{project.services.length}</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Milestones</dt>
			<dd class="mt-1 text-sm text-slate-900">{milestoneTotal}</dd>
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
				aria-label={`Milestone progress for ${project.name}`}
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
			<dd class="mt-1 text-lg font-semibold text-slate-900">{fmtPrice(totalInvoiced)}</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total paid</dt>
			<dd class="mt-1 text-lg font-semibold text-green-700">{fmtPrice(totalPaid)}</dd>
		</div>
		<div>
			<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Balance due</dt>
			<dd class="mt-1 text-lg font-semibold text-slate-900">{fmtPrice(balanceDue)}</dd>
		</div>
	</div>
</section>

<!-- Linked invoices card -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="linked-invoices-h"
>
	<div class="flex items-center justify-between">
		<h2 id="linked-invoices-h" class="text-base font-semibold text-slate-900">Linked invoices</h2>
	</div>
	{#if project.linked_invoices.length === 0}
		<p class="mt-2 text-sm text-slate-500">No invoices yet.</p>
	{:else}
		<ul class="mt-3 divide-y divide-slate-200 rounded-md border border-slate-200">
			{#each project.linked_invoices as inv (inv.id)}
				<li class="flex items-center justify-between gap-3 px-4 py-3">
					<a
						href={resolve('/client/invoices/[id]', { id: inv.id })}
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
</section>

<!-- Services section -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="services-h"
>
	<div class="border-b border-slate-200 px-6 py-4">
		<h2 id="services-h" class="text-base font-semibold text-slate-900">Services</h2>
		<p class="mt-0.5 text-sm text-slate-500">
			{project.services.length}
			{project.services.length === 1 ? 'service' : 'services'} attached
		</p>
	</div>

	{#if project.services.length === 0}
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
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each project.services as ps (ps.id)}
						{@const isCancelled = ps.status === 'cancelled'}
						<tr class={isCancelled ? 'bg-slate-50 text-slate-500' : 'hover:bg-slate-50'}>
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<span class={isCancelled ? 'line-through' : ''}>{ps.service_name}</span>
							</td>
							<td class="px-4 py-3"><StatusBadge status={ps.status} /></td>
							<td class="px-4 py-3 text-right text-sm whitespace-nowrap text-slate-700"
								>{fmtPrice(ps.price_at_attachment)}</td
							>
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
	{#if milestones.length === 0}
		<p class="mt-4 text-sm text-slate-500">No milestones yet.</p>
	{:else}
		<ul class="mt-4 divide-y divide-slate-200 rounded-md border border-slate-200">
			{#each milestones as m (m.id)}
				<li class="grid gap-2 px-4 py-3 sm:grid-cols-12 sm:items-center">
					<div class="sm:col-span-5">
						<div class="flex items-start gap-2">
							<span
								class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
								aria-hidden="true"
							>
								{m.sequence_order}
							</span>
							<p class="text-sm font-medium text-slate-900">{m.name}</p>
						</div>
					</div>
					<div class="sm:col-span-3"><StatusBadge status={m.status} /></div>
					<div class="text-xs text-slate-600 sm:col-span-4">
						<p>
							<span class="text-slate-500">Planned</span>
							{fmtDate(m.planned_date)}
						</p>
						<p class="mt-1">
							<span class="text-slate-500">Actual</span>
							{fmtDate(m.actual_date)}
						</p>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<!-- Comments section -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="comments-h"
>
	<h2 id="comments-h" class="text-base font-semibold text-slate-900">Comments</h2>
	<div class="mt-2">
		<CommentThread projectId={project.id} {fetch} {token} realm="client" staff={false} />
	</div>
</section>
