<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { navigating, page } from '$app/state';
	import Icon from '@iconify/svelte';
	import { Toaster } from 'svelte-sonner';
	import viewDashboard from '@iconify-icons/mdi/view-dashboard';
	import accountGroup from '@iconify-icons/mdi/account-group';
	import accountMultiple from '@iconify-icons/mdi/account-multiple';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import fileMultiple from '@iconify-icons/mdi/file-multiple';
	import cog from '@iconify-icons/mdi/cog';
	import accountCircle from '@iconify-icons/mdi/account-circle';
	import history from '@iconify-icons/mdi/history';
	import shieldAccount from '@iconify-icons/mdi/shield-account';
	import menu from '@iconify-icons/mdi/menu';
	import logoutVariant from '@iconify-icons/mdi/logout';
	import chevronDown from '@iconify-icons/mdi/chevron-down';
	import { assetUrl } from '$lib/api/client.js';
	import NotificationBell from '$lib/components/NotificationBell.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data, children } = $props();

	let sidebarOpen = $state(false);
	let userMenuOpen = $state(false);
	let menuRef = $state(/** @type {HTMLDivElement|null} */ (null));

	const nav = [
		{ href: '/app', label: 'Dashboard', icon: viewDashboard, exact: true, adminOnly: false },
		{ href: '/app/team', label: 'Team', icon: accountGroup, exact: false, adminOnly: false },
		{
			href: '/app/clients',
			label: 'Clients',
			icon: accountMultiple,
			exact: false,
			adminOnly: false
		},
		{
			href: '/app/projects',
			label: 'Projects',
			icon: folderMultiple,
			exact: false,
			adminOnly: false
		},
		{ href: '/app/invoices', label: 'Invoices', icon: receiptText, exact: false, adminOnly: false },
		{ href: '/app/files', label: 'Files', icon: fileMultiple, exact: false, adminOnly: false },
		{
			href: '/app/settings',
			label: 'Settings',
			icon: cog,
			exact: false,
			perm: ['manage', 'tenant_settings']
		},
		{
			href: '/app/roles',
			label: 'Roles',
			icon: shieldAccount,
			exact: false,
			perm: ['manage', 'roles']
		},
		{ href: '/app/profile', label: 'Profile', icon: accountCircle, exact: false, adminOnly: false },
		{ href: '/app/audit', label: 'Audit log', icon: history, exact: false, adminOnly: true }
	];

	let visibleNav = $derived(
		nav.filter((i) => {
			if (i.adminOnly) return auth.isTenantAdmin;
			if (i.perm) return auth.can(i.perm[0], i.perm[1]);
			return true;
		})
	);

	const brandColor = $derived(data?.profile?.branding?.color);
	const logoUrl = $derived(data?.profile?.branding?.logo_url || data?.profile?.logo_url);

	function isActive(item) {
		return item.exact ? page.url.pathname === item.href : page.url.pathname.startsWith(item.href);
	}

	function logout() {
		userMenuOpen = false;
		auth.logout();
		goto(resolve('/login'));
	}

	/**
	 * @param {string|undefined|null} name
	 */
	function getInitials(name) {
		if (!name) return 'U';
		const parts = name.trim().split(/\s+/);
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
	}

	// Close user menu on click outside or Escape
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

<svelte:head><title>{data?.profile?.business_name ?? 'ZenEngr'} — ZenEngr</title></svelte:head>

<div class="flex min-h-screen flex-col bg-slate-50">
	{#if navigating.to}
		<div
			class="fixed top-0 right-0 left-0 z-50 h-1 overflow-hidden bg-indigo-100"
			role="progressbar"
			aria-label="Loading page"
		>
			<div class="h-full w-full animate-pulse bg-indigo-600"></div>
		</div>
	{/if}
	<header
		class="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-6 print:hidden"
	>
		<div class="flex min-w-0 items-center gap-2.5">
			<button
				type="button"
				class="rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none lg:hidden"
				aria-label="Open navigation"
				aria-expanded={sidebarOpen}
				onclick={() => (sidebarOpen = true)}
			>
				<Icon icon={menu} class="h-5 w-5" />
			</button>
			<a
				href={resolve('/app/dashboard')}
				class="flex min-w-0 items-center gap-2.5 text-sm font-semibold text-slate-900 transition-opacity hover:opacity-90"
			>
				{#if logoUrl}
					<img
						src={assetUrl(logoUrl)}
						alt={`${data?.profile?.business_name ?? 'Tenant'} logo`}
						class="h-7 max-h-7 w-auto max-w-[140px] shrink-0 object-contain"
					/>
				{:else if brandColor}
					<span
						class="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
						style="background-color: {brandColor}"
						aria-hidden="true"
					></span>
				{/if}
				<span class="truncate">{data?.profile?.business_name ?? 'ZenEngr'}</span>
			</a>
		</div>
		<div class="flex min-w-0 items-center gap-2 sm:gap-3">
			<NotificationBell realm="admin" />

			<!-- User Avatar Menu -->
			<div class="relative" bind:this={menuRef}>
				<button
					type="button"
					class="group flex items-center gap-1.5 rounded-full p-1 text-slate-700 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					aria-label="User account menu"
					aria-haspopup="menu"
					aria-expanded={userMenuOpen}
					onclick={() => (userMenuOpen = !userMenuOpen)}
				>
					<div
						class="relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-xs font-bold text-white shadow-sm ring-2 ring-white group-hover:ring-indigo-200"
					>
						<span class="select-none">{getInitials(data?.user?.full_name)}</span>
						{#if data?.user?.avatar_url}
							<img
								src={assetUrl(data.user.avatar_url)}
								alt=""
								class="absolute inset-0 h-full w-full object-cover"
								onerror={(e) => { e.currentTarget.style.display = 'none'; }}
							/>
						{/if}
					</div>
					<Icon icon={chevronDown} class="hidden h-3.5 w-3.5 text-slate-400 sm:block" />
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
								<span class="select-none">{getInitials(data?.user?.full_name)}</span>
								{#if data?.user?.avatar_url}
									<img
										src={assetUrl(data.user.avatar_url)}
										alt=""
										class="absolute inset-0 h-full w-full object-cover"
										onerror={(e) => { e.currentTarget.style.display = 'none'; }}
									/>
								{/if}
							</div>
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm font-semibold text-slate-900">
									{data?.user?.full_name || 'Team Member'}
								</p>
								<p class="truncate text-xs text-slate-500">
									{data?.user?.email || ''}
								</p>
								{#if data?.user?.role}
									<div class="mt-1">
										<span
											class="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700 capitalize ring-1 ring-indigo-700/10 ring-inset"
										>
											{data.user.role}
										</span>
									</div>
								{/if}
							</div>
						</div>

						<div class="space-y-0.5 p-1">
							<a
								href={resolve('/app/profile')}
								onclick={() => (userMenuOpen = false)}
								class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus:bg-slate-100 focus:outline-none"
								role="menuitem"
							>
								<Icon icon={accountCircle} class="h-4 w-4 text-slate-500" />
								<span>Profile & Preferences</span>
							</a>

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
		</div>
	</header>

	<div class="flex flex-1 print:block print:w-full">
		<!-- Mobile and Tablet backdrop (< lg) -->
		{#if sidebarOpen}
			<button
				type="button"
				class="fixed inset-0 z-40 bg-black/40 lg:hidden"
				aria-label="Close navigation"
				onclick={() => (sidebarOpen = false)}
			></button>
		{/if}

		<aside
			class="fixed inset-y-0 left-0 z-50 w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:w-56 lg:translate-x-0 print:hidden {sidebarOpen
				? 'translate-x-0'
				: '-translate-x-full'}"
		>
			<div class="flex items-center justify-between border-b border-slate-200 px-4 py-3.5 lg:hidden">
				<span class="text-sm font-semibold text-slate-800">Navigation</span>
				<button
					type="button"
					class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
					aria-label="Close navigation"
					onclick={() => (sidebarOpen = false)}
				>
					<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			<nav aria-label="Tenant navigation" class="space-y-1 p-3">
				{#each visibleNav as item (item.href)}
					{@const active = isActive(item)}
					<a
						href={resolve(item.href)}
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
		<main
			class="mx-auto w-full max-w-7xl flex-1 p-4 transition-opacity duration-150 sm:p-6 {navigating.to
				? 'pointer-events-none opacity-50'
				: 'opacity-100'}"
		>
			{@render children()}
		</main>
	</div>
</div>

<Toaster position="top-right" richColors closeButton duration={3500} />
