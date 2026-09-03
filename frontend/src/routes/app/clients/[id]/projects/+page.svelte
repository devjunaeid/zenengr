<script>
	import Icon from '@iconify/svelte';
	import eye from '@iconify-icons/mdi/eye';
	import pencil from '@iconify-icons/mdi/pencil';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate } from '$lib/utils/format.js';

	let { data } = $props();

	let canManage = $derived(auth.can('manage', 'projects'));

	function progressPct(p) {
		if (!p.milestone_total) return 0;
		return Math.min(100, Math.round((p.milestone_completed / p.milestone_total) * 100));
	}

	function gotoPage(p) {
		const params = new SvelteURLSearchParams();
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL on the same page
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}
</script>

<svelte:head><title>Projects — {data.client.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/clients')} class="hover:text-indigo-600">Clients</a>
		</li>
		<li aria-hidden="true">/</li>
		<li>
			<a href={resolve('/app/clients/[id]', { id: data.client.id })} class="hover:text-indigo-600">
				{data.client.name}
			</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">Projects</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Projects</h1>
		<p class="mt-1 text-sm text-slate-500">
			{data.projects.total}
			{data.projects.total === 1 ? 'project' : 'projects'} for {data.client.name}
		</p>
	</div>
	{#if canManage}
		<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
		<a
			href={`${resolve('/app/projects/new')}?client_id=${data.client.id}`}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			New project
		</a>
		<!-- eslint-enable svelte/no-navigation-without-resolve -->
	{/if}
</div>

<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	{#if data.projects.items.length === 0}
		<EmptyState title="No projects yet" description="No projects yet for this client.">
			{#if canManage}
				<!-- eslint-disable svelte/no-navigation-without-resolve -- query string appended to a resolved route -->
				<a
					href={`${resolve('/app/projects/new')}?client_id=${data.client.id}`}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					New project
				</a>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
			{/if}
		</EmptyState>
	{:else}
		<!-- Mobile cards (< md): clearly separated distinct cards -->
		<div class="space-y-3 p-3 bg-slate-50/60 md:hidden">
			{#each data.projects.items as p (p.id)}
				<div class="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 transition-shadow hover:shadow-xs">
					<div class="flex items-start justify-between gap-3">
						<a
							href={resolve('/app/projects/[id]', { id: p.id })}
							class="text-sm font-bold text-indigo-600 hover:text-indigo-500"
						>
							{p.name}
						</a>
						<StatusBadge status={p.status} />
					</div>

					{#if p.milestone_total > 0}
						<div>
							<div class="mb-1 flex items-center justify-between text-xs text-slate-500">
								<span>Milestone Progress</span>
								<span>
									{p.milestone_completed}/{p.milestone_total} ({progressPct(p)}%)
								</span>
							</div>
							<div
								class="h-1.5 w-full rounded-full bg-slate-100"
								role="progressbar"
								aria-valuenow={p.milestone_completed}
								aria-valuemin={0}
								aria-valuemax={p.milestone_total}
								aria-label={`Milestone progress for ${p.name}`}
							>
								<div
									class="h-1.5 rounded-full bg-indigo-600 transition-all"
									style="width: {progressPct(p)}%"
								></div>
							</div>
						</div>
					{/if}

					<div class="flex items-center justify-between text-xs text-slate-500">
						<div>
							<span class="text-slate-400">Start date:</span>
							<span class="ml-1 font-medium text-slate-700">{formatDate(p.start_date)}</span>
						</div>
					</div>

					<div class="flex items-center justify-end gap-2 pt-1">
						<a
							href={resolve('/app/projects/[id]', { id: p.id })}
							class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
						>
							<Icon icon={eye} class="h-3.5 w-3.5 text-slate-500" />
							View
						</a>
						{#if canManage}
							<a
								href={resolve('/app/projects/[id]/edit', { id: p.id })}
								class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
							>
								<Icon icon={pencil} class="h-3.5 w-3.5 text-slate-500" />
								Edit
							</a>
						{/if}
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
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Name</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Status</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Progress</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Start</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Actions</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.projects.items as p (p.id)}
						<tr class="hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<a
									href={resolve('/app/projects/[id]', { id: p.id })}
									class="text-indigo-600 hover:text-indigo-500"
								>
									{p.name}
								</a>
							</td>
							<td class="px-4 py-3"><StatusBadge status={p.status} /></td>
							<td class="px-4 py-3 text-sm text-slate-700">
								{#if p.milestone_total > 0}
									<div class="flex items-center gap-2">
										<div
											class="h-1.5 w-24 max-w-full rounded-full bg-slate-100"
											role="progressbar"
											aria-valuenow={p.milestone_completed}
											aria-valuemin={0}
											aria-valuemax={p.milestone_total}
											aria-label={`Milestone progress for ${p.name}`}
										>
											<div
												class="h-1.5 rounded-full bg-indigo-600"
												style="width: {progressPct(p)}%"
											></div>
										</div>
										<span class="text-xs whitespace-nowrap text-slate-600"
											>{p.milestone_completed}/{p.milestone_total}</span
										>
									</div>
								{:else}
									<span class="text-xs text-slate-400">No milestones</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDate(p.start_date)}</td
							>
							<td class="px-4 py-3">
								<div class="flex items-center gap-1">
									<a
										href={resolve('/app/projects/[id]', { id: p.id })}
										aria-label="View project"
										title="View project"
										class="inline-flex rounded-md p-1.5 text-slate-600 hover:bg-slate-100 hover:text-indigo-600 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
									>
										<Icon icon={eye} class="h-4 w-4" />
									</a>
									{#if canManage}
										<a
											href={resolve('/app/projects/[id]/edit', { id: p.id })}
											aria-label="Edit project"
											title="Edit project"
											class="inline-flex rounded-md p-1.5 text-slate-600 hover:bg-slate-100 hover:text-indigo-600 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
										>
											<Icon icon={pencil} class="h-4 w-4" />
										</a>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Pagination
			page={data.projects.page}
			pageSize={data.projects.page_size}
			total={data.projects.total}
			onpage={gotoPage}
		/>
	{/if}
</div>
