<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

	let { children } = $props();

	// On public routes (login/invite), guard skipped store restore; user may be null
	const isAuthed = $derived(!!portalAuth.user && portalAuth.isClientUser);

	const nav = [
		{ href: '/client', label: 'Dashboard', exact: true },
		{ href: '/client/projects', label: 'Projects', exact: false },
		{ href: '/client/invoices', label: 'Invoices', exact: false },
		{ href: '/client/profile', label: 'Profile', exact: false }
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

<svelte:head><title>{isAuthed ? (portalAuth.tenantName || 'Client Portal') : 'Client Portal'} — ZenEngr</title></svelte:head>

{#if isAuthed}
	<div class="flex min-h-screen flex-col bg-slate-50">
		<!-- Top bar -->
		<header
			class="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 sm:px-6"
		>
			<div class="flex items-center gap-3">
				<span class="text-sm font-semibold text-slate-900">
					{portalAuth.tenantName || 'Client Portal'}
				</span>
			</div>
			<div class="flex items-center gap-3">
				<span class="hidden text-sm text-slate-700 sm:inline">{portalAuth.user?.full_name}</span>
				<button
					type="button"
					class="inline-flex items-center justify-center rounded-md p-1.5 text-slate-600 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none sm:hidden"
					onclick={() => (menuOpen = !menuOpen)}
					aria-label="Toggle menu"
					aria-expanded={menuOpen}
				>
					<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						{#if menuOpen}
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						{:else}
							<path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
						{/if}
					</svg>
				</button>
				<button
					type="button"
					onclick={logout}
					class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Log out
				</button>
			</div>
		</header>

		{#if menuOpen}
			<div
				class="fixed inset-0 z-40 bg-black/30 sm:hidden"
				onclick={() => (menuOpen = false)}
				role="presentation"
			></div>
		{/if}

		<div class="flex flex-1">
			<aside class="hidden w-56 shrink-0 border-r border-slate-200 bg-white sm:block">
				<nav aria-label="Client navigation" class="space-y-1 p-3">
					{#each nav as item (item.href)}
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

			{#if menuOpen}
				<aside
					class="fixed inset-y-0 left-0 z-50 w-64 border-r border-slate-200 bg-white shadow-lg sm:hidden"
				>
					<div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
						<span class="text-sm font-semibold text-slate-900">Menu</span>
						<button
							type="button"
							class="rounded-md p-1 text-slate-500 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
							onclick={() => (menuOpen = false)}
							aria-label="Close menu"
						>
							<svg
								class="h-5 w-5"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
					<nav aria-label="Client navigation" class="space-y-1 p-3">
						{#each nav as item (item.href)}
							{@const active = isActive(item)}
							<a
								href={resolve(/** @type {any} */ (item.href))}
								aria-current={active ? 'page' : undefined}
								onclick={() => (menuOpen = false)}
								class="block rounded-md px-3 py-2 text-sm font-medium {active
									? 'bg-indigo-50 text-indigo-700'
									: 'text-slate-700 hover:bg-slate-100'}"
							>
								{item.label}
							</a>
						{/each}
					</nav>
				</aside>
			{/if}

			<main class="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">
				{@render children()}
			</main>
		</div>
	</div>
{:else}
	<!-- Public route: render children without shell -->
	{@render children()}
{/if}
