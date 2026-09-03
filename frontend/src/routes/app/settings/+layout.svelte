<script>
	import Icon from '@iconify/svelte';
	import accountCog from '@iconify-icons/mdi/account-cog';
	import cog from '@iconify-icons/mdi/cog';
	import apps from '@iconify-icons/mdi/apps';
	import emailEdit from '@iconify-icons/mdi/email-edit';
	import bell from '@iconify-icons/mdi/bell';
	import chartBox from '@iconify-icons/mdi/chart-box';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte.js';
	import ScrollableTabs from '$lib/components/ScrollableTabs.svelte';

	const tabs = [
		{ href: '/app/settings', label: 'Business Profile', icon: accountCog, exact: true },
		{
			href: '/app/settings/configuration',
			label: 'Configuration',
			icon: cog,
			exact: false
		},
		{ href: '/app/settings/email', label: 'Email (SMTP)', icon: emailEdit, exact: false },
		{ href: '/app/settings/notifications', label: 'Notifications', icon: bell, exact: false },
		{ href: '/app/settings/plan', label: 'Plan & Usage', icon: chartBox, exact: false },
		{
			href: '/app/settings/services',
			label: 'Services',
			icon: apps,
			exact: false,
			perm: ['view', 'services']
		}
	];

	let visibleTabs = $derived(tabs.filter((t) => (t.perm ? auth.can(t.perm[0], t.perm[1]) : true)));

	let { children } = $props();

	function isActive(tab) {
		return tab.exact ? page.url.pathname === tab.href : page.url.pathname.startsWith(tab.href);
	}
</script>

<div class="mx-auto w-full max-w-5xl space-y-6">
	<!-- Tab Navigation Header -->
	<header class="border-b border-slate-200/80 pb-4">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h1 class="text-2xl font-bold tracking-tight text-slate-900">Tenant Settings</h1>
				<p class="mt-1 text-sm text-slate-500">
					Manage organization branding, regional formats, invoice defaults, and team preferences.
				</p>
			</div>
		</div>

		<!-- Segmented Navigation Pill Bar -->
		<ScrollableTabs ariaLabel="Settings navigation" class="mt-5">
			{#each visibleTabs as tab (tab.href)}
				{@const active = isActive(tab)}
				<a
					href={resolve(tab.href)}
					aria-current={active ? 'page' : undefined}
					class="group inline-flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all {active
						? 'bg-indigo-600 text-white shadow-2xs'
						: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
				>
					<Icon
						icon={tab.icon}
						class="h-4 w-4 shrink-0 transition-colors {active
							? 'text-white'
							: 'text-slate-400 group-hover:text-slate-600'}"
					/>
					<span>{tab.label}</span>
				</a>
			{/each}
		</ScrollableTabs>
	</header>

	<main>
		{@render children()}
	</main>
</div>
