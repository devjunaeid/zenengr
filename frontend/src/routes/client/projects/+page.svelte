<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Icon from '@iconify/svelte';
	import magnify from '@iconify-icons/mdi/magnify';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import arrowRight from '@iconify-icons/mdi/arrow-right';
	import calendarRange from '@iconify-icons/mdi/calendar-range';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { formatDate, humanize, formatProjectCode } from '$lib/utils/format.js';

	let { data } = $props();

	let search = $state(untrack(() => data.filters.q || ''));
	let status = $state(untrack(() => data.filters.status || ''));

	let hasFilter = $derived(Boolean(untrack(() => data.filters.status || data.filters.q)));

	const statusOptions = ['', 'active', 'completed', 'on_hold', 'draft', 'cancelled'];

	function buildUrl(p, newSearch = search, newStatus = status) {
		const params = new SvelteURLSearchParams();
		if (newStatus) params.set('status', newStatus);
		if (newSearch.trim()) params.set('q', newSearch.trim());
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/client/projects')}?${qs}` : resolve('/client/projects');
	}

	function applyFilters() {
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(buildUrl(1, search, status));
	}

	function gotoPage(p) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(buildUrl(p, search, status));
	}

	function progressPct(p) {
		if (!p.milestone_total) return 0;
		return Math.min(100, Math.round((p.milestone_completed / p.milestone_total) * 100));
	}
</script>

<svelte:head><title>Projects — Client Portal</title></svelte:head>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-xl font-bold text-slate-900">Projects</h1>
			<p class="mt-0.5 text-xs text-slate-500">
				{data.projects.total}
				{data.projects.total === 1 ? 'project' : 'projects'} assigned to your account
			</p>
		</div>
	</div>

	<!-- Search and Filter Bar -->
	<div class="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
		<form
			class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
			onsubmit={(e) => {
				e.preventDefault();
				applyFilters();
			}}
		>
			<div class="relative min-w-0 flex-1 sm:max-w-md">
				<Icon
					icon={magnify}
					class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400"
				/>
				<input
					type="text"
					bind:value={search}
					placeholder="Search projects by name..."
					class="w-full rounded-lg border-slate-300 py-1.5 pr-4 pl-9 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>

			<div class="flex items-center gap-2.5 w-full sm:w-auto">
				<select
					id="f-status"
					bind:value={status}
					onchange={applyFilters}
					class="w-full flex-1 sm:flex-none rounded-lg border-slate-300 py-1.5 pr-8 pl-3 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 sm:w-auto"
				>
					<option value="">All Statuses</option>
					{#each statusOptions.filter(Boolean) as opt (opt)}
						<option value={opt}>{humanize(opt)}</option>
					{/each}
				</select>
				<button
					type="submit"
					class="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700"
				>
					Search
				</button>
			</div>
		</form>
	</div>

	<!-- Projects Grid / List -->
	{#if data.projects.items.length === 0}
		<div class="rounded-xl border border-slate-200 bg-white p-8 shadow-2xs">
			{#if hasFilter}
				<div class="py-6 text-center">
					<p class="text-xs text-slate-500">No projects match your search query or filter.</p>
					<button
						type="button"
						onclick={() => {
							search = '';
							status = '';
							applyFilters();
						}}
						class="mt-3 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
					>
						Clear filters
					</button>
				</div>
			{:else}
				<EmptyState
					title="No projects yet"
					description="Your projects will appear here once they are created by your service provider."
				/>
			{/if}
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
			{#each data.projects.items as proj (proj.id)}
				{@const pct = progressPct(proj)}
				<a
					href={resolve('/client/projects/[id]', { id: proj.id })}
					class="group flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-2xs transition-all hover:border-indigo-300 hover:shadow-sm"
				>
					<div>
						<div class="flex items-start justify-between gap-3">
							<div class="flex min-w-0 items-center gap-2.5">
								<div
									class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"
								>
									<Icon icon={folderMultiple} class="h-5 w-5" />
								</div>
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<h2
											class="line-clamp-1 min-w-0 text-sm font-bold text-slate-900 transition-colors group-hover:text-indigo-600"
										>
											{proj.name}
										</h2>
										<span
											class="shrink-0 rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-500"
										>
											{formatProjectCode(proj.id)}
										</span>
									</div>
									{#if proj.start_date}
										<p class="mt-0.5 flex items-center gap-1 text-[11px] text-slate-500">
											<Icon icon={calendarRange} class="h-3 w-3 text-slate-400" />
											Started {formatDate(proj.start_date)}
										</p>
									{/if}
								</div>
							</div>
							<StatusBadge status={proj.status} />
						</div>

						<!-- Progress Section -->
						<div class="mt-4 border-t border-slate-100 pt-3">
							<div class="flex justify-between gap-2 text-[11px] font-semibold">
								<span class="text-slate-500">
									{#if proj.milestone_total > 0}
										{proj.milestone_completed} of {proj.milestone_total} milestones completed
									{:else}
										Ongoing work
									{/if}
								</span>
								<span class="text-slate-900">{pct}%</span>
							</div>
							<div class="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
								<div
									class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-indigo-600 transition-all duration-300"
									style="width: {pct}%"
								></div>
							</div>
						</div>
					</div>

					<div
						class="mt-4 flex items-center justify-end text-xs font-semibold text-indigo-600 group-hover:text-indigo-700"
					>
						<span>View Details</span>
						<Icon
							icon={arrowRight}
							class="ml-1 h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
						/>
					</div>
				</a>
			{/each}
		</div>

		<Pagination
			page={data.projects.page}
			pageSize={data.projects.page_size}
			total={data.projects.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
