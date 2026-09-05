<script>
	import Icon from '@iconify/svelte';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import arrowRight from '@iconify-icons/mdi/arrow-right';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { resolve } from '$app/paths';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { fmtPrice } from '$lib/utils/format.js';

	let { data } = $props();

	// Layout guard guarantees these exist
	const user = /** @type {import('$lib/api/portal.js').PortalUser} */ (portalAuth.user);
	const client = /** @type {import('$lib/api/portal.js').PortalClient} */ (portalAuth.client);

	function progressPct(p) {
		if (!p.milestone_total) return 0;
		return Math.min(100, Math.round((p.milestone_completed / p.milestone_total) * 100));
	}
</script>

<svelte:head><title>Dashboard — Client Portal</title></svelte:head>

<div class="space-y-6">
	<!-- Welcome Banner -->
	<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex items-center gap-4">
				<div
					class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-base font-bold text-white shadow-sm"
				>
					{client.name.slice(0, 2).toUpperCase()}
				</div>
				<div>
					<h1 class="text-xl font-bold text-slate-900">
						Welcome back, {user.full_name}
					</h1>
					<div class="mt-1 flex items-center gap-2">
						<span class="text-xs font-semibold text-slate-600">{client.name}</span>
						<StatusBadge status={client.status} />
					</div>
				</div>
			</div>

			<div class="flex flex-wrap items-center gap-2.5">
				<a
					href={resolve('/client/projects')}
					class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700"
				>
					<Icon icon={folderMultiple} class="h-4 w-4" />
					View Projects
				</a>
				<a
					href={resolve('/client/invoices')}
					class="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50"
				>
					<Icon icon={receiptText} class="h-4 w-4 text-slate-500" />
					View Invoices
				</a>
			</div>
		</div>
	</section>

	<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
		<!-- Active Projects Overview -->
		<section
			class="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-2xs"
		>
			<div>
				<div
					class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3"
				>
					<div class="flex shrink-0 items-center gap-2">
						<Icon icon={folderMultiple} class="h-5 w-5 text-indigo-600" />
						<h2 class="text-sm font-bold text-slate-900">Recent Projects</h2>
					</div>
					<a
						href={resolve('/client/projects')}
						class="flex shrink-0 items-center gap-1 text-xs font-semibold whitespace-nowrap text-indigo-600 hover:text-indigo-700"
					>
						All ({data.projects.total})
						<Icon icon={arrowRight} class="h-3.5 w-3.5" />
					</a>
				</div>

				{#if data.projects.items.length === 0}
					<div class="py-8 text-center">
						<p class="text-xs text-slate-500">No projects set up yet.</p>
					</div>
				{:else}
					<div class="divide-y divide-slate-100">
						{#each data.projects.items as proj (proj.id)}
							{@const pct = progressPct(proj)}
							<a
								href={resolve('/client/projects/[id]', { id: proj.id })}
								class="group -mx-2 flex items-center justify-between rounded-lg px-2 py-3.5 transition-colors hover:bg-slate-50/70"
							>
								<div class="min-w-0 pr-3">
									<p
										class="truncate text-xs font-bold text-slate-900 transition-colors group-hover:text-indigo-600"
									>
										{proj.name}
									</p>
									<div class="mt-1 flex items-center gap-2">
										<StatusBadge status={proj.status} />
										{#if proj.milestone_total > 0}
											<span class="text-[11px] text-slate-500">
												{proj.milestone_completed}/{proj.milestone_total} milestones
											</span>
										{/if}
									</div>
								</div>
								<div class="w-20 shrink-0 text-right">
									<span class="text-[11px] font-bold text-slate-700">{pct}%</span>
									<div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
										<div
											class="h-full rounded-full bg-indigo-600 transition-all"
											style="width: {pct}%"
										></div>
									</div>
								</div>
							</a>
						{/each}
					</div>
				{/if}
			</div>
		</section>

		<!-- Recent Invoices Overview -->
		<section
			class="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-2xs"
		>
			<div>
				<div
					class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3"
				>
					<div class="flex shrink-0 items-center gap-2">
						<Icon icon={receiptText} class="h-5 w-5 text-indigo-600" />
						<h2 class="text-sm font-bold text-slate-900">Recent Invoices</h2>
					</div>
					<a
						href={resolve('/client/invoices')}
						class="flex shrink-0 items-center gap-1 text-xs font-semibold whitespace-nowrap text-indigo-600 hover:text-indigo-700"
					>
						All ({data.invoices.total})
						<Icon icon={arrowRight} class="h-3.5 w-3.5" />
					</a>
				</div>

				{#if data.invoices.items.length === 0}
					<div class="py-8 text-center">
						<p class="text-xs text-slate-500">No invoices issued yet.</p>
					</div>
				{:else}
					<div class="divide-y divide-slate-100">
						{#each data.invoices.items as inv (inv.id)}
							<a
								href={resolve('/client/invoices/[id]', { id: inv.id })}
								class="group -mx-2 flex items-center justify-between rounded-lg px-2 py-3.5 transition-colors hover:bg-slate-50/70"
							>
								<div class="min-w-0 pr-3">
									<p
										class="text-xs font-bold text-slate-900 transition-colors group-hover:text-indigo-600"
									>
										{inv.invoice_number ?? 'Invoice'}
									</p>
									<p class="truncate text-[11px] text-slate-500">
										{inv.project_name || 'Project invoice'}
									</p>
								</div>
								<div class="shrink-0 text-right">
									<p class="text-xs font-bold text-slate-900">{fmtPrice(inv.total)}</p>
									<div class="mt-0.5">
										<StatusBadge status={inv.status} />
									</div>
								</div>
							</a>
						{/each}
					</div>
				{/if}
			</div>
		</section>
	</div>
</div>
