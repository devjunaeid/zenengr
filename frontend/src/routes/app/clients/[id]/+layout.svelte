<script>
	import Icon from '@iconify/svelte';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';

	let { data, children } = $props();

	// Derived so the tab bar tracks navigation between clients (the layout
	// component is reused across /app/clients/:id navigations).
	let tabs = $derived([
		{
			href: `/app/clients/${data.client.id}`,
			label: 'Overview',
			icon: 'mdi:view-dashboard',
			exact: true
		},
		{
			href: `/app/clients/${data.client.id}/projects`,
			label: 'Projects',
			icon: 'mdi:folder-multiple',
			exact: false
		},
		{
			href: `/app/clients/${data.client.id}/invoices`,
			label: 'Invoices',
			icon: 'mdi:receipt-text',
			exact: false
		}
	]);

	/**
	 * @param {{ href: string, icon: string, exact: boolean }} tab
	 */
	function isActive(tab) {
		return tab.exact ? page.url.pathname === tab.href : page.url.pathname.startsWith(tab.href);
	}
</script>

<nav
	class="mb-6 flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1.5 shadow-sm"
	aria-label="Client sections"
>
	{#each tabs as tab (tab.href)}
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
