<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import AuditLogList from '$lib/components/AuditLogList.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import { AUDIT_ACTION_OPTIONS } from '$lib/utils/audit.js';

	let { data } = $props();

	let action = $state(untrack(() => data.filters.action));
	let from = $state(untrack(() => data.filters.from));
	let to = $state(untrack(() => data.filters.to));

	function gotoPage(page) {
		goto(
			// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
			`${resolve('/app/audit')}?action=${encodeURIComponent(action)}&from=${from}&to=${to}&page=${page}`
		);
	}

	function applyFilters() {
		gotoPage(1);
	}
</script>

<svelte:head><title>Audit log — ZenEngr</title></svelte:head>

<h1 class="text-2xl font-semibold text-slate-900">Audit log</h1>
<p class="mt-1 text-sm text-slate-500">{data.audit.total} events</p>

<form
	class="mt-6 flex flex-wrap items-end gap-3"
	onsubmit={(e) => {
		e.preventDefault();
		applyFilters();
	}}
>
	<div>
		<label for="f-action" class="block text-xs font-medium text-slate-600">Action</label>
		<select
			id="f-action"
			bind:value={action}
			class="mt-1 block w-72 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		>
			<option value="">All actions</option>
			{#each AUDIT_ACTION_OPTIONS as group (group.group)}
				<optgroup label={group.group}>
					{#each group.items as item (item.value)}
						<option value={item.value}>{item.label}</option>
					{/each}
				</optgroup>
			{/each}
		</select>
	</div>
	<div>
		<label for="f-from" class="block text-xs font-medium text-slate-600">From</label>
		<input
			id="f-from"
			type="date"
			bind:value={from}
			class="mt-1 block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>
	<div>
		<label for="f-to" class="block text-xs font-medium text-slate-600">To</label>
		<input
			id="f-to"
			type="date"
			bind:value={to}
			class="mt-1 block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>
	<button
		type="submit"
		class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		Apply
	</button>
</form>

<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	{#if data.audit.items.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">
			No results match your search. Try different filters.
		</p>
	{:else}
		<AuditLogList entries={data.audit.items} />
		<Pagination
			page={data.audit.page}
			pageSize={data.audit.page_size}
			total={data.audit.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
