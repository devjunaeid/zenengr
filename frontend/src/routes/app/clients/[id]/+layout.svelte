<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';

	let { data, children } = $props();

	// Derived so the tab bar tracks navigation between clients (the layout
	// component is reused across /app/clients/:id navigations).
	let tabs = $derived([
		{ href: `/app/clients/${data.client.id}`, label: 'Overview', exact: true },
		{ href: `/app/clients/${data.client.id}/projects`, label: 'Projects', exact: false },
		{ href: `/app/clients/${data.client.id}/invoices`, label: 'Invoices', exact: false }
	]);

	/**
	 * @param {{ href: string, exact: boolean }} tab
	 */
	function isActive(tab) {
		return tab.exact ? page.url.pathname === tab.href : page.url.pathname.startsWith(tab.href);
	}
</script>

<nav class="mb-6 flex flex-wrap gap-1" aria-label="Client sections">
	{#each tabs as tab (tab.href)}
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
