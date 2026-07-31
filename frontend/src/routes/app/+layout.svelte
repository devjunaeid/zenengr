<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data, children } = $props();

	const nav = [
		{ href: '/app', label: 'Dashboard', exact: true, adminOnly: false },
		{ href: '/app/team', label: 'Team', exact: false, adminOnly: false },
		{ href: '/app/clients', label: 'Clients', exact: false, adminOnly: false },
		{ href: '/app/settings', label: 'Settings', exact: false, adminOnly: true },
		{ href: '/app/audit', label: 'Audit log', exact: false, adminOnly: true }
	];

	let visibleNav = $derived(nav.filter((i) => !i.adminOnly || auth.isTenantAdmin));

	/**
	 * @param {{ href: string, exact: boolean }} item
	 */
	function isActive(item) {
		return item.exact ? page.url.pathname === item.href : page.url.pathname.startsWith(item.href);
	}

	function logout() {
		auth.logout();
		goto(resolve('/login'));
	}
</script>

<svelte:head><title>{data.profile.business_name} — ZenEngr</title></svelte:head>

<div class="flex min-h-screen flex-col bg-slate-50">
	<header class="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
		<span class="text-sm font-semibold text-slate-900">{data.profile.business_name}</span>
		<div class="flex items-center gap-4">
			<span class="text-sm text-slate-700">
				{data.user.full_name}
				<span class="text-slate-400">({data.user.role})</span>
			</span>
			<button
				type="button"
				onclick={logout}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Log out
			</button>
		</div>
	</header>

	<div class="flex flex-1">
		<aside class="w-56 shrink-0 border-r border-slate-200 bg-white">
			<nav aria-label="Tenant navigation" class="space-y-1 p-3">
				{#each visibleNav as item (item.href)}
					{@const active = isActive(item)}
					<a
						href={resolve(/** @type {any} */ (item.href))}
						aria-current={active ? 'page' : undefined}
						class="block rounded-md px-3 py-2 text-sm font-medium {active
							? 'bg-indigo-50 text-indigo-700'
							: 'text-slate-700 hover:bg-slate-100'}"
					>
						{item.label}
					</a>
				{/each}
			</nav>
		</aside>
		<main class="mx-auto w-full max-w-7xl flex-1 p-6">
			{@render children()}
		</main>
	</div>
</div>
