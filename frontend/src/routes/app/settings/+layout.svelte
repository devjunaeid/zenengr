<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte.js';

	/** @type {Array<{ href: string, label: string, exact: boolean, perm?: [string, string] }>} */
	const tabs = [
		{ href: '/app/settings', label: 'Business profile', exact: true },
		{ href: '/app/settings/configuration', label: 'Configuration', exact: false },
		{ href: '/app/settings/email', label: 'Email (SMTP)', exact: false },
		{ href: '/app/settings/plan', label: 'Plan & usage', exact: false },
		{ href: '/app/settings/services', label: 'Services', exact: false, perm: ['view', 'services'] }
	];

	let visibleTabs = $derived(tabs.filter((t) => (t.perm ? auth.can(t.perm[0], t.perm[1]) : true)));

	let { children } = $props();

	/**
	 * @param {{ href: string, exact: boolean }} tab
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
				class="rounded-md px-3 py-1.5 text-sm font-medium {active
					? 'bg-indigo-50 text-indigo-700'
					: 'text-slate-700 hover:bg-slate-100'}"
			>
				{tab.label}
			</a>
		{/each}
	</nav>

	{@render children()}
</div>
