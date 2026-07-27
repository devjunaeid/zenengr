<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { children } = $props();

	const nav = [
		{ href: '/admin/tenants', label: 'Tenants' },
		{ href: '/admin/plans', label: 'Plans' }
	];

	function logout() {
		auth.logout();
		goto(resolve('/login'));
	}
</script>

<svelte:head><title>Super Admin — ZenEngr</title></svelte:head>

<div class="flex min-h-screen bg-slate-50">
	<aside class="w-60 shrink-0 border-r border-slate-200 bg-white">
		<div class="border-b border-slate-200 px-5 py-4">
			<span class="block text-sm font-semibold text-slate-900">ZenEngr Platform</span>
			<span class="block text-xs text-slate-500">Super Admin Console</span>
		</div>
		<nav aria-label="Super admin navigation" class="space-y-1 p-3">
			{#each nav as item (item.href)}
				{@const active = page.url.pathname.startsWith(item.href)}
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

	<div class="flex min-w-0 flex-1 flex-col">
		<header
			class="flex items-center justify-end gap-4 border-b border-slate-200 bg-white px-6 py-3"
		>
			<span class="text-sm text-slate-700">
				{auth.user?.full_name}
				<span class="text-slate-400">({auth.user?.email})</span>
			</span>
			<button
				type="button"
				onclick={logout}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Log out
			</button>
		</header>
		<main class="mx-auto w-full max-w-7xl flex-1 p-6">
			{@render children()}
		</main>
	</div>
</div>
