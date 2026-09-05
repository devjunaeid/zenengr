<script>
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, fmtPrice } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import plus from '@iconify-icons/mdi/plus';
	import magnify from '@iconify-icons/mdi/magnify';
	import shapeOutline from '@iconify-icons/mdi/shape-outline';

	let { data } = $props();

	let canManage = $derived(auth.can('manage', 'services'));
	let hasFilter = $derived(
		Boolean(untrack(() => data.filters.q)) || Boolean(untrack(() => data.filters.is_active))
	);

	let q = $state(untrack(() => data.filters.q));
	let isActive = $state(untrack(() => data.filters.is_active));

	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (q) params.set('q', q);
		if (isActive) params.set('is_active', isActive);
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/app/settings/services')}?${qs}` : resolve('/app/settings/services');
	}

	function applyFilters() {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(1));
	}

	function gotoPage(p) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(p));
	}
</script>

<svelte:head><title>Services — ZenEngr</title></svelte:head>

<div class="space-y-6">
	<!-- Top Action Header & Filter Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h2 class="text-base font-bold text-slate-900">
					Service Catalog &amp; Milestone Templates
				</h2>
				<p class="mt-0.5 text-xs text-slate-500">
					Predefined service packages with reusable milestone sequences used when creating projects.
				</p>
			</div>

			{#if canManage}
				<a
					href={resolve('/app/settings/services/new')}
					class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<Icon icon={plus} class="h-4 w-4" />
					Add New Service
				</a>
			{/if}
		</div>

		<!-- Filter Bar -->
		<form
			class="mt-4 flex flex-col gap-2.5 border-t border-slate-100 pt-4 sm:flex-row sm:items-center"
			onsubmit={(e) => {
				e.preventDefault();
				applyFilters();
			}}
		>
			<div class="w-full sm:flex-1">
				<label for="f-q" class="block text-xs font-medium text-slate-600">Search</label>
				<div class="relative mt-1">
					<Icon icon={magnify} class="absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
					<input
						id="f-q"
						type="search"
						bind:value={q}
						placeholder="Search services by name or description..."
						class="w-full rounded-lg border border-slate-200 bg-slate-50/50 py-2 pr-3 pl-9 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-indigo-500 focus:bg-white focus:ring-1 focus:ring-indigo-500 focus:outline-none"
					/>
				</div>
			</div>

			<div class="flex items-center gap-2">
				<div class="w-full sm:w-auto">
					<label for="f-status" class="block text-xs font-medium text-slate-600">Status</label>
					<select
						id="f-status"
						bind:value={isActive}
						class="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2 text-xs text-slate-700 shadow-2xs focus:border-indigo-500 focus:bg-white focus:ring-1 focus:ring-indigo-500 focus:outline-none sm:w-auto"
					>
						<option value="">All Statuses</option>
						<option value="active">Active Only</option>
						<option value="inactive">Inactive Only</option>
					</select>
				</div>

				<button
					type="submit"
					class="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50"
				>
					Filter
				</button>
			</div>
		</form>
	</section>

	<!-- Services List Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		{#if data.services.items.length === 0}
			{#if hasFilter}
				<div class="p-12 text-center">
					<Icon icon={shapeOutline} class="mx-auto h-8 w-8 text-slate-300" />
					<p class="mt-2 text-xs font-semibold text-slate-700">No services match your filters</p>
					<p class="mt-1 text-xs text-slate-400">Try resetting your search query.</p>
				</div>
			{:else}
				<div class="p-12 text-center">
					<Icon icon={shapeOutline} class="mx-auto h-10 w-10 text-slate-300" />
					<h3 class="mt-3 text-sm font-bold text-slate-900">No services created yet</h3>
					<p class="mx-auto mt-1 max-w-sm text-xs text-slate-500">
						Create your first service template to start attaching services and standard milestone
						steps to client projects.
					</p>
					{#if canManage}
						<a
							href={resolve('/app/settings/services/new')}
							class="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700"
						>
							<Icon icon={plus} class="h-4 w-4" />
							Create First Service
						</a>
					{/if}
				</div>
			{/if}
		{:else}
			<!-- Mobile cards (< md): clearly separated distinct cards -->
			<div class="space-y-3 bg-slate-50/60 p-3 md:hidden">
				{#each data.services.items as s (s.id)}
					<div
						class="space-y-3 rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs transition-shadow hover:shadow-xs"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<a
									href={resolve('/app/settings/services/[id]', { id: s.id })}
									class="text-sm font-bold text-indigo-600 hover:text-indigo-700"
								>
									{s.name}
								</a>
								{#if s.description}
									<p class="mt-0.5 line-clamp-2 text-xs text-slate-500">{s.description}</p>
								{/if}
							</div>
							<StatusBadge status={s.is_active ? 'active' : 'inactive'} />
						</div>

						<div class="grid grid-cols-2 gap-2 rounded-lg bg-slate-50 p-2.5 text-xs">
							<div>
								<span class="text-slate-400">Default Price:</span>
								<span class="ml-1 font-bold text-slate-900">{fmtPrice(s.default_price)}</span>
							</div>
							<div>
								<span class="text-slate-400">Milestones:</span>
								<span class="ml-1 font-semibold text-slate-700">
									{s.step_count}
									{s.step_count === 1 ? 'step' : 'steps'}
								</span>
							</div>
							<div class="col-span-2">
								<span class="text-slate-400">Created:</span>
								<span class="ml-1 text-slate-600">{formatDate(s.created_at)}</span>
							</div>
						</div>

						<div class="flex justify-end pt-1">
							<a
								href={resolve('/app/settings/services/[id]', { id: s.id })}
								class="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
							>
								Configure service
							</a>
						</div>
					</div>
				{/each}
			</div>

			<!-- Desktop table (>= md) -->
			<div class="relative hidden overflow-x-auto md:block">
				<table class="min-w-full divide-y divide-slate-200">
					<thead class="bg-slate-50">
						<tr>
							<th
								scope="col"
								class="px-6 py-3.5 text-left text-xs font-semibold tracking-wider text-slate-600 uppercase"
							>
								Service Name
							</th>
							<th
								scope="col"
								class="px-6 py-3.5 text-left text-xs font-semibold tracking-wider text-slate-600 uppercase"
							>
								Description
							</th>
							<th
								scope="col"
								class="px-6 py-3.5 text-right text-xs font-semibold tracking-wider text-slate-600 uppercase"
							>
								Default Price
							</th>
							<th
								scope="col"
								class="px-6 py-3.5 text-center text-xs font-semibold tracking-wider text-slate-600 uppercase"
							>
								Milestone Steps
							</th>
							<th
								scope="col"
								class="px-6 py-3.5 text-center text-xs font-semibold tracking-wider text-slate-600 uppercase"
							>
								Status
							</th>
							<th
								scope="col"
								class="px-6 py-3.5 text-right text-xs font-semibold tracking-wider text-slate-600 uppercase"
							>
								Created
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-200 bg-white">
						{#each data.services.items as s (s.id)}
							<tr class="transition-colors hover:bg-slate-50/50">
								<td class="px-6 py-4">
									<a
										href={resolve('/app/settings/services/[id]', { id: s.id })}
										class="text-sm font-bold text-indigo-600 hover:text-indigo-700"
									>
										{s.name}
									</a>
								</td>
								<td class="max-w-xs px-6 py-4 text-xs text-slate-500">
									{#if s.description}
										<span class="line-clamp-2">{s.description}</span>
									{:else}
										<span class="text-slate-400 italic">No description</span>
									{/if}
								</td>
								<td class="px-6 py-4 text-right text-xs font-bold whitespace-nowrap text-slate-900">
									{fmtPrice(s.default_price)}
								</td>
								<td class="px-6 py-4 text-center">
									<span
										class="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700"
									>
										{s.step_count}
										{s.step_count === 1 ? 'step' : 'steps'}
									</span>
								</td>
								<td class="px-6 py-4 text-center">
									<StatusBadge status={s.is_active ? 'active' : 'inactive'} />
								</td>
								<td class="px-6 py-4 text-right text-xs whitespace-nowrap text-slate-500">
									{formatDate(s.created_at)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<div class="border-t border-slate-100 p-4">
				<Pagination
					page={data.services.page}
					pageSize={data.services.page_size}
					total={data.services.total}
					onpage={gotoPage}
				/>
			</div>
		{/if}
	</section>
</div>
