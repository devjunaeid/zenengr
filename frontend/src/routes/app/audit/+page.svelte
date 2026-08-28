<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import AuditLogList from '$lib/components/AuditLogList.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import AuditActionSelect from '$lib/components/AuditActionSelect.svelte';
	import Icon from '@iconify/svelte';
	import history from '@iconify-icons/mdi/history';
	import filterVariant from '@iconify-icons/mdi/filter-variant';
	import filterRemove from '@iconify-icons/mdi/filter-remove';

	let { data } = $props();

	let action = $state(untrack(() => data?.filters?.action ?? ''));
	let from = $state(untrack(() => data?.filters?.from ?? ''));
	let to = $state(untrack(() => data?.filters?.to ?? ''));

	let hasFilters = $derived(Boolean(action) || Boolean(from) || Boolean(to));

	let auditItems = $derived(data?.audit?.items ?? []);
	let auditTotal = $derived(data?.audit?.total ?? 0);
	let auditPage = $derived(data?.audit?.page ?? 1);
	let auditPageSize = $derived(data?.audit?.page_size ?? 20);

	function gotoPage(page) {
		const params = new URLSearchParams();
		if (action) params.set('action', action);
		if (from) params.set('from', from);
		if (to) params.set('to', to);
		if (page > 1) params.set('page', String(page));
		const qs = params.toString();
		goto(qs ? `${resolve('/app/audit')}?${qs}` : resolve('/app/audit'));
	}

	function applyFilters() {
		gotoPage(1);
	}

	function resetFilters() {
		action = '';
		from = '';
		to = '';
		goto(resolve('/app/audit'));
	}
</script>

<svelte:head><title>Audit Log — ZenEngr</title></svelte:head>

<div class="space-y-6">
	{#if data?.error}
		<div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-800 shadow-2xs">
			<span class="font-bold">Error loading audit events:</span> {data.error}
		</div>
	{/if}

	<!-- Audit Log Header & Filter Card -->
	<section class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs relative z-20">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex items-center gap-3">
				<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
					<Icon icon={history} class="h-5 w-5" />
				</div>
				<div>
					<h1 class="text-base font-bold text-slate-900">Tenant Audit &amp; Activity Trail</h1>
					<p class="text-xs text-slate-500 mt-0.5">
						Append-only immutable record of all client, project, invoice, and security events.
					</p>
				</div>
			</div>

			<span class="inline-flex items-center rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">
				{auditTotal} {auditTotal === 1 ? 'logged event' : 'logged events'}
			</span>
		</div>

		<!-- Filter Bar -->
		<form
			class="mt-4 flex flex-wrap items-end gap-3 border-t border-slate-100 pt-4"
			onsubmit={(e) => {
				e.preventDefault();
				applyFilters();
			}}
		>
			<div class="flex-1 min-w-[260px]">
				<label for="f-action" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
					Event Action
				</label>
				<AuditActionSelect id="f-action" bind:value={action} />
			</div>

			<div>
				<label for="f-from" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
					From Date
				</label>
				<input
					id="f-from"
					type="date"
					bind:value={from}
					class="block rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
				/>
			</div>

			<div>
				<label for="f-to" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
					To Date
				</label>
				<input
					id="f-to"
					type="date"
					bind:value={to}
					class="block rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
				/>
			</div>

			<div class="flex items-center gap-2">
				<button
					type="submit"
					class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition-colors"
				>
					<Icon icon={filterVariant} class="h-3.5 w-3.5" />
					Filter
				</button>
				{#if hasFilters}
					<button
						type="button"
						onclick={resetFilters}
						class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
					>
						<Icon icon={filterRemove} class="h-3.5 w-3.5 text-slate-500" />
						Reset
					</button>
				{/if}
			</div>
		</form>
	</section>

	<!-- Audit Log List Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		{#if auditItems.length === 0}
			{#if hasFilters}
				<div class="p-12 text-center">
					<Icon icon={history} class="mx-auto h-8 w-8 text-slate-300" />
					<p class="mt-2 text-xs font-bold text-slate-800">No matching audit events</p>
					<p class="text-xs text-slate-400 mt-1">No activities match the selected action or date range filter.</p>
					<button
						type="button"
						onclick={resetFilters}
						class="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
					>
						Reset all filters
					</button>
				</div>
			{:else}
				<div class="p-12 text-center">
					<Icon icon={history} class="mx-auto h-10 w-10 text-slate-300" />
					<h3 class="mt-3 text-sm font-bold text-slate-900">No audit activity recorded yet</h3>
					<p class="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
						Actions performed by your team — including project status changes, invoices issued, file uploads, and settings updates — will automatically appear here in real-time.
					</p>
				</div>
			{/if}
		{:else}
			<AuditLogList entries={auditItems} />
			<div class="border-t border-slate-100 p-4">
				<Pagination
					page={auditPage}
					pageSize={auditPageSize}
					total={auditTotal}
					onpage={gotoPage}
				/>
			</div>
		{/if}
	</section>
</div>
