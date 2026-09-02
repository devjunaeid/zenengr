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
	import { assetUrl } from '$lib/api/client.js';
	import NotificationBell from '$lib/components/NotificationBell.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data, children } = $props();

	let sidebarOpen = $state(false);

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
		auth.logout();
		goto(resolve('/login'));
	}
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
		class="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-6 print:hidden"
	>
		<div class="flex min-w-0 items-center gap-2.5">
			<button
				type="button"
				class="rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none md:hidden"
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
		<div class="flex min-w-0 items-center gap-3 sm:gap-4">
			<NotificationBell realm="admin" />
			<span class="min-w-0 truncate text-sm text-slate-700">
				{data?.user?.full_name ?? ''}
				<span class="text-slate-400">({data?.user?.role ?? ''})</span>
			</span>
			<button
				type="button"
				onclick={logout}
				class="shrink-0 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Log out
			</button>
		</div>
	</header>

	<div class="flex flex-1 print:block print:w-full">
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
			class="fixed inset-y-0 left-0 z-50 w-56 shrink-0 overflow-y-auto border-r border-slate-200 bg-white transition-transform duration-200 md:static md:translate-x-0 print:hidden {sidebarOpen
				? 'translate-x-0'
				: '-translate-x-full'}"
		>
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
