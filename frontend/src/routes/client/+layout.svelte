<script>
	import Icon from '@iconify/svelte';
	import viewDashboard from '@iconify-icons/mdi/view-dashboard';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import accountCircle from '@iconify-icons/mdi/account-circle';
	import menu from '@iconify-icons/mdi/menu';
	import logoutVariant from '@iconify-icons/mdi/logout';
	import chevronDown from '@iconify-icons/mdi/chevron-down';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import NotificationBell from '$lib/components/NotificationBell.svelte';
	import { assetUrl } from '$lib/api/client.js';

	let { children } = $props();

	// On public routes (login/invite), guard skipped store restore; user may be null
	const isAuthed = $derived(!!portalAuth.user && portalAuth.isClientUser);

	/** @type {Array<{ href: string, label: string, icon: any, exact: boolean }>} */
	const nav = [
		{ href: '/client', label: 'Dashboard', icon: viewDashboard, exact: true },
		{ href: '/client/projects', label: 'Projects', icon: folderMultiple, exact: false },
		{ href: '/client/invoices', label: 'Invoices', icon: receiptText, exact: false },
		{ href: '/client/profile', label: 'Profile', icon: accountCircle, exact: false }
	];

	/** @param {{ href: string, exact: boolean }} item */
	function isActive(item) {
		return item.exact ? page.url.pathname === item.href : page.url.pathname.startsWith(item.href);
	}

	function logout() {
		userMenuOpen = false;
		portalAuth.logout();
		goto(resolve('/client/login'));
	}

	let menuOpen = $state(false);
	let userMenuOpen = $state(false);
	let menuRef = $state(/** @type {HTMLDivElement|null} */ (null));

	/**
	 * @param {string|undefined|null} name
	 */
	function getInitials(name) {
		if (!name) return 'C';
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

<svelte:head
	><title>{isAuthed ? portalAuth.tenantName || 'Client Portal' : 'Client Portal'} — ZenEngr</title
	></svelte:head
>

{#if isAuthed}
	<div class="flex min-h-screen bg-slate-50 print:block">
		<!-- Mobile and Tablet backdrop (< lg) -->
		{#if menuOpen}
			<button
				type="button"
				class="fixed inset-0 z-40 bg-black/40 lg:hidden print:hidden"
				aria-label="Close navigation"
				onclick={() => (menuOpen = false)}
			></button>
		{/if}

		<aside
			class="fixed inset-y-0 left-0 z-50 w-64 shrink-0 border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:w-60 lg:translate-x-0 print:hidden {menuOpen
				? 'translate-x-0'
				: '-translate-x-full'}"
		>
			<div class="flex items-center justify-between border-b border-slate-200 px-5 py-4">
				<a
					href={resolve('/client/projects')}
					class="flex items-center gap-2.5 text-sm font-semibold text-slate-900 transition-opacity hover:opacity-90"
				>
					{#if portalAuth.tenantLogoUrl}
						<img
							src={assetUrl(portalAuth.tenantLogoUrl)}
							alt={`${portalAuth.tenantName || 'Tenant'} logo`}
							class="h-7 max-h-7 w-auto max-w-[120px] shrink-0 object-contain"
						/>
					{/if}
					<span class="min-w-0 truncate">{portalAuth.tenantName || 'Client Portal'}</span>
				</a>
				<button
					type="button"
					class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 lg:hidden"
					aria-label="Close navigation"
					onclick={() => (menuOpen = false)}
				>
					<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			<nav aria-label="Client navigation" class="space-y-1 overflow-y-auto p-3">
				{#each nav as item (item.href)}
					{@const active = isActive(item)}
					<a
						href={resolve(/** @type {any} */ (item.href))}
						aria-current={active ? 'page' : undefined}
						onclick={() => (menuOpen = false)}
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

		<div class="flex min-w-0 flex-1 flex-col print:w-full">
			<header
				class="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-6 print:hidden"
			>
				<button
					type="button"
					class="rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none lg:hidden"
					aria-label="Toggle navigation"
					aria-expanded={menuOpen}
					onclick={() => (menuOpen = !menuOpen)}
				>
					<Icon icon={menu} class="h-5 w-5" />
				</button>
				<div class="ml-auto flex items-center gap-2 sm:gap-3">
					<NotificationBell realm="client" />

					<!-- User Avatar Menu -->
					<div class="relative" bind:this={menuRef}>
						<button
							type="button"
							class="group flex items-center gap-1.5 rounded-full p-1 text-slate-700 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
							aria-label="Client account menu"
							aria-haspopup="menu"
							aria-expanded={userMenuOpen}
							onclick={() => (userMenuOpen = !userMenuOpen)}
						>
							<div
								class="relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-xs font-bold text-white shadow-sm ring-2 ring-white group-hover:ring-indigo-200"
							>
								<span class="select-none">{getInitials(portalAuth.user?.full_name)}</span>
								{#if portalAuth.user?.avatar_url}
									<img
										src={assetUrl(portalAuth.user.avatar_url)}
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
										<span class="select-none">{getInitials(portalAuth.user?.full_name)}</span>
										{#if portalAuth.user?.avatar_url}
											<img
												src={assetUrl(portalAuth.user.avatar_url)}
												alt=""
												class="absolute inset-0 h-full w-full object-cover"
												onerror={(e) => { e.currentTarget.style.display = 'none'; }}
											/>
										{/if}
									</div>
									<div class="min-w-0 flex-1">
										<p class="truncate text-sm font-semibold text-slate-900">
											{portalAuth.user?.full_name || 'Client User'}
										</p>
										<p class="truncate text-xs text-slate-500">
											{portalAuth.user?.email || ''}
										</p>
										{#if portalAuth.tenantName}
											<p class="mt-0.5 truncate text-xs font-medium text-indigo-600">
												{portalAuth.tenantName}
											</p>
										{/if}
									</div>
								</div>

								<div class="space-y-0.5 p-1">
									<a
										href={resolve('/client/profile')}
										onclick={() => (userMenuOpen = false)}
										class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus:bg-slate-100 focus:outline-none"
										role="menuitem"
									>
										<Icon icon={accountCircle} class="h-4 w-4 text-slate-500" />
										<span>Profile & Account</span>
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
			<main class="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">
				{@render children()}
			</main>
		</div>
	</div>
{:else}
	<!-- Public route: render children without shell -->
	{@render children()}
{/if}
