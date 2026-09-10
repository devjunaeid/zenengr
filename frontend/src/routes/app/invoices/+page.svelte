<script>
	import { onMount, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Icon from '@iconify/svelte';
	import close from '@iconify-icons/mdi/close';
	import filterVariant from '@iconify-icons/mdi/filter-variant';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import * as projectApi from '$lib/api/projects.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	let status = $state(untrack(() => data.filters.status));
	let invoiceType = $state(untrack(() => data.filters.type));
	let projectId = $state(untrack(() => data.filters.project_id));
	let dateFrom = $state(untrack(() => data.filters.date_from));
	let dateTo = $state(untrack(() => data.filters.date_to));

	/** @type {import('$lib/api/projects.js').ProjectPickerItem[]} */
	let projectOptions = $state([]);

	onMount(async () => {
		try {
			const res = await projectApi.getProjectPicker(fetch, auth.token, { limit: 20 });
			projectOptions = res.items ?? [];
		} catch (err) {
			console.error('Failed to load project filter options:', err);
		}
	});

	let hasFilter = $derived(
		Boolean(status) ||
			Boolean(invoiceType) ||
			Boolean(projectId) ||
			Boolean(dateFrom) ||
			Boolean(dateTo)
	);

	const statusOptions = ['', 'draft', 'issued', 'partially_paid', 'paid', 'void'];
	const typeOptions = [
		{ value: '', label: 'All types' },
		{ value: 'project', label: 'Project invoices' },
		{ value: 'general', label: 'General invoices' }
	];

	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (status) params.set('status', status);
		if (invoiceType) params.set('type', invoiceType);
		if (projectId && invoiceType !== 'general') params.set('project_id', projectId);
		if (dateFrom) params.set('date_from', dateFrom);
		if (dateTo) params.set('date_to', dateTo);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/app/invoices')}?${qs}` : resolve('/app/invoices');
	}

	function applyFilters() {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(1));
	}

	function clearFilters() {
		status = '';
		invoiceType = '';
		projectId = '';
		dateFrom = '';
		dateTo = '';
		goto(resolve('/app/invoices'));
	}

	function gotoPage(p) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(p));
	}
</script>

<svelte:head><title>Invoices — ZenEngr</title></svelte:head>

<div class="flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Invoices</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.invoices?.total ?? 0}
			{(data.invoices?.total ?? 0) === 1 ? 'invoice' : 'invoices'}
		</p>
	</div>
	<a
		href={resolve('/app/invoices/new')}
		class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		New invoice
	</a>
</div>

{#if data.loadError}
	<div
		class="mt-4 flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-2xs"
	>
		<span>{data.loadError}</span>
		<button
			type="button"
			onclick={() => window.location.reload()}
			class="font-medium underline hover:text-amber-900 focus-visible:outline-none"
		>
			Retry
		</button>
	</div>
{/if}

<!-- ══════════════════════════════════════════════════════════════ -->
<!-- Filter Bar -->
<!-- ══════════════════════════════════════════════════════════════ -->
<form
	class="mt-6 space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs"
	onsubmit={(e) => {
		e.preventDefault();
		applyFilters();
	}}
>
	<div class="flex items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
		<span
			class="flex items-center gap-1.5 text-xs font-bold tracking-wider text-slate-700 uppercase"
		>
			<Icon icon={filterVariant} class="h-3.5 w-3.5 text-slate-400" /> Filters
		</span>
		{#if hasFilter}
			<button
				type="button"
				onclick={clearFilters}
				class="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
			>
				<Icon icon={close} class="h-3 w-3" /> Clear filters
			</button>
		{/if}
	</div>

	<div class="grid grid-cols-1 items-end gap-3 sm:grid-cols-2 lg:grid-cols-5">
		<!-- 1. Type Filter -->
		<div>
			<label for="f-type" class="block text-xs font-semibold text-slate-600">Type</label>
			<select
				id="f-type"
				bind:value={invoiceType}
				class="mt-1 block w-full rounded-lg border-slate-300 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
			>
				{#each typeOptions as opt (opt.value)}
					<option value={opt.value}>{opt.label}</option>
				{/each}
			</select>
		</div>

		<!-- 2. Status Filter -->
		<div>
			<label for="f-status" class="block text-xs font-semibold text-slate-600">Status</label>
			<select
				id="f-status"
				bind:value={status}
				class="mt-1 block w-full rounded-lg border-slate-300 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
			>
				{#each statusOptions as opt (opt)}
					<option value={opt}>{opt === '' ? 'All statuses' : humanize(opt)}</option>
				{/each}
			</select>
		</div>

		<!-- 3. Project Filter -->
		<div>
			<label for="f-project" class="block text-xs font-semibold text-slate-600">Project</label>
			<select
				id="f-project"
				bind:value={projectId}
				disabled={invoiceType === 'general'}
				class="mt-1 block w-full rounded-lg border-slate-300 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100 disabled:text-slate-400"
			>
				<option value="">All projects</option>
				{#if projectId && !projectOptions.some((p) => p.id === projectId)}
					<option value={projectId}>Selected Project</option>
				{/if}
				{#each projectOptions as p (p.id)}
					<option value={p.id}>{p.name}</option>
				{/each}
			</select>
		</div>

		<!-- 4. Date From Filter -->
		<div>
			<label for="f-date-from" class="block text-xs font-semibold text-slate-600">From date</label>
			<input
				id="f-date-from"
				type="date"
				bind:value={dateFrom}
				class="mt-1 block w-full rounded-lg border-slate-300 px-2.5 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>

		<!-- 5. Date To Filter -->
		<div>
			<label for="f-date-to" class="block text-xs font-semibold text-slate-600">To date</label>
			<input
				id="f-date-to"
				type="date"
				bind:value={dateTo}
				class="mt-1 block w-full rounded-lg border-slate-300 px-2.5 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>
	</div>

	<div class="flex justify-end gap-2 pt-1">
		{#if hasFilter}
			<button
				type="button"
				onclick={clearFilters}
				class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-2xs hover:bg-slate-50"
			>
				Reset
			</button>
		{/if}
		<button
			type="submit"
			class="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-slate-900"
		>
			Apply filters
		</button>
	</div>
</form>

<!-- ══════════════════════════════════════════════════════════════ -->
<!-- Invoice List Table & Cards -->
<!-- ══════════════════════════════════════════════════════════════ -->
<div class="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
	{#if data.invoices.items.length === 0}
		{#if hasFilter}
			<div class="px-6 py-12 text-center">
				<p class="text-sm font-medium text-slate-900">No invoices match your filters</p>
				<p class="mt-1 text-xs text-slate-500">
					Try clearing or broadening your search and date filters.
				</p>
				<button
					type="button"
					onclick={clearFilters}
					class="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
				>
					Clear filters
				</button>
			</div>
		{:else}
			<EmptyState
				title="No invoices yet"
				description="Create a project invoice or general invoice to get started."
			>
				<a
					href={resolve('/app/invoices/new')}
					class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					New invoice
				</a>
			</EmptyState>
		{/if}
	{:else}
		<!-- Mobile & Tablet cards (< lg): responsive grid -->
		<div class="grid grid-cols-1 gap-3.5 bg-slate-50/60 p-3 sm:grid-cols-2 lg:hidden">
			{#each data.invoices.items as inv (inv.id)}
				{@const projectName =
					inv.project_name ?? projectOptions.find((p) => p.id === inv.project_id)?.name}
				<div
					class="flex flex-col justify-between space-y-3 rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs transition-shadow hover:shadow-xs"
				>
					<div class="space-y-3">
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<a
									href={resolve('/app/invoices/[id]', { id: inv.id })}
									class="font-mono text-sm font-bold text-indigo-600 hover:text-indigo-500"
								>
									{inv.invoice_number ?? 'Draft Invoice'}
								</a>
								<div class="mt-0.5 text-xs">
									{#if inv.project_id}
										<span class="font-medium text-slate-700">{projectName ?? '—'}</span>
									{:else}
										<div class="flex items-center gap-1.5">
											<span
												class="py-0.2 inline-flex items-center rounded-full bg-slate-100 px-1.5 text-[10px] font-medium text-slate-600 ring-1 ring-slate-500/20"
											>
												General
											</span>
											{#if inv.billed_to && inv.billed_to.name}
												<span class="truncate font-medium text-slate-900">
													{inv.billed_to.name}
												</span>
											{/if}
										</div>
									{/if}
								</div>
							</div>
							<div class="flex flex-col items-end gap-1">
								<StatusBadge status={inv.status} />
								{#if inv.is_auto}
									<span
										class="py-0.2 inline-flex items-center rounded-full bg-violet-100 px-1.5 text-[10px] font-medium text-violet-800"
									>
										Statement
									</span>
								{/if}
							</div>
						</div>

						<div class="flex items-center justify-between rounded-lg bg-slate-50 p-2.5">
							<span class="text-xs text-slate-500">Total Amount</span>
							<span class="text-sm font-bold text-slate-900">{fmtPrice(inv.total)}</span>
						</div>

						<div class="grid grid-cols-2 gap-2 text-xs text-slate-500">
							<div>
								<span class="text-slate-400">Issued:</span>
								<span class="ml-1 text-slate-700">{formatDate(inv.issue_date)}</span>
							</div>
							<div>
								<span class="text-slate-400">Created:</span>
								<span class="ml-1 text-slate-700">{formatDate(inv.created_at)}</span>
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-1">
						<a
							href={resolve('/app/invoices/[id]', { id: inv.id })}
							class="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
						>
							View invoice
						</a>
					</div>
				</div>
			{/each}
		</div>

		<!-- Desktop table (>= lg) -->
		<div class="relative hidden overflow-x-auto lg:block">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>
							Invoice number
						</th>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>
							Type / Recipient
						</th>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>
							Status
						</th>
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>
							Total
						</th>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>
							Issued
						</th>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>
							Created
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.invoices.items as inv (inv.id)}
						{@const projectName =
							inv.project_name ?? projectOptions.find((p) => p.id === inv.project_id)?.name}
						<tr class="transition-colors hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/invoices/[id]', { id: inv.id })}
									class="font-mono font-semibold text-indigo-600 hover:text-indigo-500"
								>
									{inv.invoice_number ?? 'Draft'}
								</a>
							</td>
							<td class="px-4 py-3 text-sm text-slate-700">
								{#if inv.project_id}
									<div class="flex items-center gap-1.5">
										<span
											class="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-indigo-600/20"
										>
											Project
										</span>
										<span class="font-medium text-slate-900">{projectName ?? '—'}</span>
									</div>
								{:else}
									<div class="flex items-center gap-1.5">
										<span
											class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-500/20"
										>
											General
										</span>
										{#if inv.billed_to && inv.billed_to.name}
											<span class="font-medium text-slate-900">{inv.billed_to.name}</span>
										{:else}
											<span class="text-slate-400 italic">Internal</span>
										{/if}
									</div>
								{/if}
							</td>
							<td class="px-4 py-3">
								<span class="flex flex-wrap items-center gap-2">
									<StatusBadge status={inv.status} />
									{#if inv.is_auto}
										<span
											title="Statement invoice — internal, project-scoped"
											class="inline-flex items-center rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800 ring-1 ring-violet-600/20 ring-inset"
										>
											Statement
										</span>
									{/if}
								</span>
							</td>
							<td
								class="px-4 py-3 text-right font-mono text-sm font-semibold whitespace-nowrap text-slate-900"
							>
								{fmtPrice(inv.total)}
							</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600">
								{formatDate(inv.issue_date)}
							</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600">
								{formatDate(inv.created_at)}
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
