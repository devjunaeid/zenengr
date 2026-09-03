<script>
	import { resolve } from '$app/paths';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { humanize } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import folderPlusOutline from '@iconify-icons/mdi/folder-plus-outline';
	import accountPlusOutline from '@iconify-icons/mdi/account-plus-outline';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import accountGroup from '@iconify-icons/mdi/account-group';
	import arrowRight from '@iconify-icons/mdi/arrow-right';

	let { data } = $props();

	const quickActions = [
		{
			title: 'New Project',
			description: 'Create a client project and attach service milestones',
			href: resolve('/app/projects/new'),
			icon: folderPlusOutline,
			color: 'text-indigo-600 bg-indigo-50 hover:border-indigo-300'
		},
		{
			title: 'Add Client',
			description: 'Onboard a corporate or individual client profile',
			href: resolve('/app/clients/new'),
			icon: accountPlusOutline,
			color: 'text-emerald-600 bg-emerald-50 hover:border-emerald-300'
		},
		{
			title: 'Issue Invoice',
			description: 'Draft milestone or retainer billing for projects',
			href: resolve('/app/invoices/new'),
			icon: receiptText,
			color: 'text-violet-600 bg-violet-50 hover:border-violet-300'
		},
		{
			title: 'Manage Team',
			description: 'Invite employees, assign roles and manage access',
			href: resolve('/app/team'),
			icon: accountGroup,
			color: 'text-amber-600 bg-amber-50 hover:border-amber-300'
		}
	];
</script>

<svelte:head><title>Dashboard — ZenEngr</title></svelte:head>

<div class="space-y-6">
	<!-- Welcome & Plan Banner -->
	<div>
		<h1 class="text-2xl font-bold text-slate-900">Dashboard</h1>
		<p class="mt-1 text-sm text-slate-500">
			Welcome back, {auth.user?.full_name}. Active Plan: <span class="font-bold text-indigo-600">{data.plan.plan_name}</span>
		</p>
	</div>

	<!-- Plan Quota Limits & Usage Cards -->
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		{#each Object.entries(data.plan.limits) as [key, limit] (key)}
			{@const used = data.plan.usage[key.replace(/^max_/, '')] ?? 0}
			<div class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
				<p class="text-xs font-semibold tracking-wider text-slate-500 uppercase">{humanize(key)}</p>
				<p class="mt-2 text-2xl font-bold text-slate-900">
					{used}<span class="text-sm font-normal text-slate-400"> / {limit}</span>
				</p>
				<div
					class="mt-3 h-1.5 w-full rounded-full bg-slate-100"
					role="progressbar"
					aria-valuenow={used}
					aria-valuemin={0}
					aria-valuemax={limit}
					aria-label={`${humanize(key)} usage`}
				>
					<div
						class="h-1.5 rounded-full bg-indigo-600 transition-all"
						style="width: {Math.min(100, limit > 0 ? (used / limit) * 100 : 0)}%"
					></div>
				</div>
			</div>
		{/each}
	</div>

	<!-- Quick Actions Hub -->
	<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs" aria-labelledby="quick-actions-h">
		<div class="mb-4">
			<h2 id="quick-actions-h" class="text-base font-bold text-slate-900">Quick Actions</h2>
			<p class="mt-0.5 text-xs text-slate-500">Fast shortcuts to common operational tasks and management workflows.</p>
		</div>

		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<!-- eslint-disable svelte/no-navigation-without-resolve -- pre-resolved via resolve() in quickActions array -->
			{#each quickActions as action (action.title)}
				<a
					href={action.href}
					class="group flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs transition-all hover:shadow-xs {action.color.split(' ').pop()}"
				>
					<div>
						<div class="flex h-10 w-10 items-center justify-center rounded-xl {action.color.split(' ').slice(0, 2).join(' ')}">
							<Icon icon={action.icon} class="h-5 w-5" />
						</div>
						<h3 class="mt-3 text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{action.title}</h3>
						<p class="mt-1 text-xs text-slate-500 leading-relaxed">{action.description}</p>
					</div>

					<div class="mt-4 flex items-center gap-1 text-xs font-semibold text-indigo-600 group-hover:text-indigo-700 pt-2 border-t border-slate-100">
						<span>Start now</span>
						<Icon icon={arrowRight} class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
					</div>
				</a>
			{/each}
			<!-- eslint-enable svelte/no-navigation-without-resolve -->
		</div>
	</section>
</div>
