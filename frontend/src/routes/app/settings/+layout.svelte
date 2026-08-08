<script>
	import Icon from '@iconify/svelte';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte.js';

	/** @type {Array<{ href: string, label: string, icon: string, exact: boolean, perm?: [string, string] }>} */
	const tabs = [
		{ href: '/app/settings', label: 'Business profile', icon: 'mdi:account-cog', exact: true },
		{
			href: '/app/settings/configuration',
			label: 'Configuration',
			icon: 'mdi:cog',
			exact: false
		},
		{ href: '/app/settings/email', label: 'Email (SMTP)', icon: 'mdi:email-cog', exact: false },
		{ href: '/app/settings/plan', label: 'Plan & usage', icon: 'mdi:chart-box', exact: false },
		{
			href: '/app/settings/services',
			label: 'Services',
			icon: 'mdi:apps',
			exact: false,
			perm: ['view', 'services']
		}
	];

	let visibleTabs = $derived(tabs.filter((t) => (t.perm ? auth.can(t.perm[0], t.perm[1]) : true)));

	let { children } = $props();

	/**
	 * @param {{ href: string, icon: string, exact: boolean }} tab
	 */
	function isActive(tab) {
		return tab.exact ? page.url.pathname === tab.href : page.url.pathname.startsWith(tab.href);
	}
</script>

<div class="mx-auto w-full max-w-5xl">
	<nav class="mb-6 flex flex-wrap gap-1" aria-label="Settings sections">
		{#each visibleTabs as tab (tab.href)}
			{@const active = isActive(tab)}
			<a
				href={resolve(/** @type {any} */ (tab.href))}
				aria-current={active ? 'page' : undefined}
				class="inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium {active
					? 'bg-indigo-600 text-white'
					: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}"
			>
				<Icon icon={tab.icon} class="h-4 w-4" />
				{tab.label}
			</a>
		{/each}
	</nav>

	{@render children()}
</div>
