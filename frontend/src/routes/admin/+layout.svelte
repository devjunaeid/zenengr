<script>
	import Icon from '@iconify/svelte';
	import officeBuilding from '@iconify-icons/mdi/office-building';
	import chartBox from '@iconify-icons/mdi/chart-box';
	import menu from '@iconify-icons/mdi/menu';
	import logoutVariant from '@iconify-icons/mdi/logout';
	import chevronDown from '@iconify-icons/mdi/chevron-down';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { assetUrl } from '$lib/api/client.js';

	let { children } = $props();

	let sidebarOpen = $state(false);
	let userMenuOpen = $state(false);
	let menuRef = $state(/** @type {HTMLDivElement|null} */ (null));

	/** @type {Array<{ href: string, label: string, icon: any }>} */
	const nav = [
		{ href: '/admin/tenants', label: 'Tenants', icon: officeBuilding },
		{ href: '/admin/plans', label: 'Plans', icon: chartBox }
	];

	function logout() {
		userMenuOpen = false;
		auth.logout();
		goto(resolve('/login'));
	}

	/**
	 * @param {string|undefined|null} name
	 */
	function getInitials(name) {
		if (!name) return 'SA';
		const parts = name.trim().split(/\s+/);
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
	}

	// Close user menu on outside click or Escape
	$effect(() => {
		if (!userMenuOpen || !menuRef) return;
		/** @param {PointerEvent} e */
		function onPointerDown(e) {
			const target = /** @type {Node|null} */ (e.target);
			if (target && menuRef && !menuRef.contains(target)) {
				userMenuOpen = false;
			}
		}
		/** @param {KeyboardEvent} e */
		function onKeydown(e) {
			if (e.key === 'Escape') userMenuOpen = false;
		}
		document.addEventListener('pointerdown', onPointerDown);
		document.addEventListener('keydown', onKeydown);
		return () => {
			document.removeEventListener('pointerdown', onPointerDown);
			document.removeEventListener('keydown', onKeydown);
		};
	});
</script>

<svelte:head><title>Super Admin — ZenEngr</title></svelte:head>

<div class="flex min-h-screen bg-slate-50">
	<!-- Mobile backdrop -->
	{#if sidebarOpen}
		<button
			type="button"
			class="fixed inset-0 z-40 bg-black/40 md:hidden"
			aria-label="Close navigation"
			onclick={() => (sidebarOpen = false)}
		></button>
	{/if}

	<aside
		class="fixed inset-y-0 left-0 z-50 w-60 shrink-0 border-r border-slate-200 bg-white transition-transform duration-200 md:static md:translate-x-0 {sidebarOpen
			? 'translate-x-0'
			: '-translate-x-full'}"
	>
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
					onclick={() => (sidebarOpen = false)}
					class="group flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium {active
						? 'bg-indigo-600 text-white shadow-sm'
						: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}"
				>
					<Icon
						icon={item.icon}
						class="h-4 w-4 shrink-0 {active ? '' : 'text-slate-500 group-hover:text-slate-700'}"
					/>
					{item.label}
				</a>
			{/each}
		</nav>
	</aside>

	<div class="flex min-w-0 flex-1 flex-col">
		<header
			class="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-6"
		>
			<div class="flex items-center gap-3">
				<button
					type="button"
					class="rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none md:hidden"
					aria-label="Open navigation"
					aria-expanded={sidebarOpen}
					onclick={() => (sidebarOpen = true)}
				>
					<Icon icon={menu} class="h-5 w-5" />
				</button>
				<span class="text-sm font-semibold text-slate-800 md:hidden">Super Admin</span>
			</div>

			<!-- User Avatar Menu -->
			<div class="relative ml-auto" bind:this={menuRef}>
				<button
					type="button"
					class="group flex items-center gap-2 rounded-full p-1 text-slate-700 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					aria-label="Account menu"
					aria-haspopup="menu"
					aria-expanded={userMenuOpen}
					onclick={() => (userMenuOpen = !userMenuOpen)}
				>
					<div
						class="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-xs font-bold text-white shadow-sm ring-2 ring-white group-hover:ring-indigo-200"
					>
						<span class="select-none">{getInitials(auth.user?.full_name)}</span>
						{#if auth.user?.avatar_url}
							<img
								src={assetUrl(auth.user.avatar_url)}
								alt=""
								class="absolute inset-0 h-full w-full object-cover"
								onerror={(e) => { e.currentTarget.style.display = 'none'; }}
							/>
						{/if}
					</div>
					<Icon icon={chevronDown} class="hidden h-4 w-4 text-slate-400 sm:block" />
				</button>

				{#if userMenuOpen}
					<div
						class="absolute right-0 z-50 mt-2 w-64 origin-top-right rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg ring-1 ring-black/5 focus:outline-none"
						role="menu"
						aria-orientation="vertical"
					>
						<div class="flex items-center gap-3 border-b border-slate-100 px-3 py-2.5">
							<div
								class="relative flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-xs font-bold text-white shadow-xs ring-1 ring-slate-200"
							>
								<span class="select-none">{getInitials(auth.user?.full_name)}</span>
								{#if auth.user?.avatar_url}
									<img
										src={assetUrl(auth.user.avatar_url)}
										alt=""
										class="absolute inset-0 h-full w-full object-cover"
										onerror={(e) => { e.currentTarget.style.display = 'none'; }}
									/>
								{/if}
							</div>
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm font-semibold text-slate-900">
									{auth.user?.full_name || 'Admin User'}
								</p>
								<p class="truncate text-xs text-slate-500">
									{auth.user?.email || 'admin@zenengr.dev'}
								</p>
								<div class="mt-1">
									<span
										class="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700 ring-1 ring-indigo-700/10 ring-inset"
									>
										Super Admin
									</span>
								</div>
							</div>
						</div>

						<div class="p-1">
							<button
								type="button"
								role="menuitem"
								onclick={logout}
								class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium text-rose-600 transition-colors hover:bg-rose-50 focus:bg-rose-50 focus:outline-none"
							>
								<Icon icon={logoutVariant} class="h-4 w-4" />
								<span>Log out</span>
							</button>
						</div>
					</div>
				{/if}
			</div>
		</header>
		<main class="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">
			{@render children()}
		</main>
	</div>
</div>
