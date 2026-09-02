<script>
	import Icon from '@iconify/svelte';
	import viewDashboard from '@iconify-icons/mdi/view-dashboard';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import accountCircle from '@iconify-icons/mdi/account-circle';
	import menu from '@iconify-icons/mdi/menu';
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
		portalAuth.logout();
		goto(resolve('/client/login'));
	}

	let menuOpen = $state(false);
</script>

<svelte:head
	><title>{isAuthed ? portalAuth.tenantName || 'Client Portal' : 'Client Portal'} — ZenEngr</title
	></svelte:head
>

{#if isAuthed}
	<div class="flex min-h-screen bg-slate-50 print:block">
		<!-- Mobile backdrop -->
		{#if menuOpen}
			<button
				type="button"
				class="fixed inset-0 z-40 bg-black/40 md:hidden print:hidden"
				aria-label="Close navigation"
				onclick={() => (menuOpen = false)}
			></button>
		{/if}

		<aside
			class="fixed inset-y-0 left-0 z-50 w-60 shrink-0 border-r border-slate-200 bg-white transition-transform duration-200 md:static md:translate-x-0 print:hidden {menuOpen
				? 'translate-x-0'
				: '-translate-x-full'}"
		>
			<div class="border-b border-slate-200 px-5 py-4">
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
				class="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-6 print:hidden"
			>
				<button
					type="button"
					class="rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none md:hidden"
					aria-label="Toggle navigation"
					aria-expanded={menuOpen}
					onclick={() => (menuOpen = !menuOpen)}
				>
					<Icon icon={menu} class="h-5 w-5" />
				</button>
				<span class="ml-auto hidden min-w-0 truncate text-sm text-slate-700 sm:inline">
					{portalAuth.user?.full_name}
				</span>
				<NotificationBell realm="client" />
				<button
					type="button"
					onclick={logout}
					class="shrink-0 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Log out
				</button>
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
