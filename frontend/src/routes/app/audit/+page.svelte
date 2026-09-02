<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
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
		const params = new SvelteURLSearchParams();
		if (action) params.set('action', action);
		if (from) params.set('from', from);
		if (to) params.set('to', to);
		if (page > 1) params.set('page', String(page));
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
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
		<div
			role="alert"
			class="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-800 shadow-2xs"
		>
			<span class="font-bold">Error loading audit events:</span>
			{data.error}
		</div>
	{/if}

	<!-- Audit Log Header & Filter Card -->
	<section class="relative z-20 rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex items-center gap-3">
				<div
					class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"
				>
					<Icon icon={history} class="h-5 w-5" />
				</div>
				<div>
					<h1 class="text-base font-bold text-slate-900">Tenant Audit &amp; Activity Trail</h1>
					<p class="mt-0.5 text-xs text-slate-500">
						Append-only immutable record of all client, project, invoice, and security events.
					</p>
				</div>
			</div>

			<span
				class="inline-flex shrink-0 items-center rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700"
			>
				{auditTotal}
				{auditTotal === 1 ? 'logged event' : 'logged events'}
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
			<div class="min-w-[260px] flex-1">
				<label
					for="f-action"
					class="mb-1.5 block text-xs font-semibold tracking-wider text-slate-600 uppercase"
				>
					Event Action
				</label>
				<AuditActionSelect id="f-action" bind:value={action} />
			</div>

			<div class="w-full sm:w-auto">
				<label
					for="f-from"
					class="mb-1.5 block text-xs font-semibold tracking-wider text-slate-600 uppercase"
				>
					From Date
				</label>
				<input
					id="f-from"
					type="date"
					bind:value={from}
					class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs shadow-2xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none sm:w-auto"
				/>
			</div>

			<div class="w-full sm:w-auto">
				<label
					for="f-to"
					class="mb-1.5 block text-xs font-semibold tracking-wider text-slate-600 uppercase"
				>
					To Date
				</label>
				<input
					id="f-to"
					type="date"
					bind:value={to}
					class="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs shadow-2xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none sm:w-auto"
				/>
			</div>

			<div class="flex items-center gap-2">
				<button
					type="submit"
					class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<Icon icon={filterVariant} class="h-3.5 w-3.5" />
					Filter
				</button>
				{#if hasFilters}
					<button
						type="button"
						onclick={resetFilters}
						class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50"
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
					<p class="mt-1 text-xs text-slate-400">
						No activities match the selected action or date range filter.
					</p>
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
					<p class="mx-auto mt-1 max-w-sm text-xs text-slate-500">
						Actions performed by your team — including project status changes, invoices issued, file
						uploads, and settings updates — will automatically appear here in real-time.
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
