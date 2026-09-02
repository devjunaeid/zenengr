<script>
	import Icon from '@iconify/svelte';
	import viewDashboard from '@iconify-icons/mdi/view-dashboard';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';

	let { data, children } = $props();

	// Derived so the tab bar tracks navigation between clients
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

<!-- Breadcrumb Header -->
<nav aria-label="Breadcrumb" class="mb-4 text-xs font-semibold text-slate-500">
	<ol class="flex items-center gap-1.5">
		<li>
			<a href={resolve('/app/clients')} class="transition-colors hover:text-indigo-600">Clients</a>
		</li>
		<li aria-hidden="true" class="text-slate-300">/</li>
		<li class="font-bold text-slate-800">{data.client.name}</li>
	</ol>
</nav>

<!-- Client Top Navigation Bar -->
<nav
	class="mb-6 flex gap-1.5 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-2xs"
	aria-label="Client sections"
>
	{#each tabs as tab (tab.href)}
		{@const active = isActive(tab)}
		<a
			href={resolve(tab.href)}
			aria-current={active ? 'page' : undefined}
			class="group inline-flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold whitespace-nowrap transition-all {active
				? 'bg-indigo-600 text-white shadow-2xs'
				: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
		>
			<Icon
				icon={tab.icon}
				class="h-4 w-4 shrink-0 {active
					? 'text-white'
					: 'text-slate-400 group-hover:text-slate-600'}"
			/>
			{tab.label}
		</a>
	{/each}
</nav>

{@render children()}
