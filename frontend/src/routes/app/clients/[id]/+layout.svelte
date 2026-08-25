<script>
	import Icon from '@iconify/svelte';
	import viewDashboard from '@iconify-icons/mdi/view-dashboard';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';

	let { data, children } = $props();

	// Derived so the tab bar tracks navigation between clients (the layout
	// component is reused across /app/clients/:id navigations).
	let tabs = $derived([
		{
			href: `/app/clients/${data.client.id}`,
			label: 'Overview',
			icon: viewDashboard,
			exact: true
		},
		{
			href: `/app/clients/${data.client.id}/projects`,
			label: 'Projects',
			icon: folderMultiple,
			exact: false
		},
		{
			href: `/app/clients/${data.client.id}/invoices`,
			label: 'Invoices',
			icon: receiptText,
			exact: false
		}
	]);

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
			href={resolve(tab.href)}
			aria-current={active ? 'page' : undefined}
			class="group inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium {active
				? 'bg-indigo-600 text-white shadow-sm'
				: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}"
		>
			<Icon
				icon={tab.icon}
				class="h-4 w-4 shrink-0 {active ? '' : 'text-slate-500 group-hover:text-slate-700'}"
			/>
			{tab.label}
		</a>
	{/each}
</nav>

{@render children()}
