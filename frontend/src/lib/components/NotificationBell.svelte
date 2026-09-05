<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { notifications } from '$lib/stores/notifications.svelte.js';
	import { timeAgo } from '$lib/utils/format.js';

	/**
	 * Notification bell + dropdown panel (FEAT-017). Self-initializes on
	 * mount using the auth store matching its realm; tears down on logout
	 * (token becomes null). The underlying store keeps exactly one socket
	 * per realm across navigations.
	 *
	 * @type {{
	 *   realm: import('$lib/api/notifications.js').NotificationRealm
	 * }}
	 */
	let { realm = 'admin' } = $props();

	const store = $derived(notifications.realm(realm));
	const authStore = $derived(realm === 'client' ? portalAuth : auth);
	let open = $state(false);
	let rootEl = $state(/** @type {HTMLDivElement|null} */ (null));

	/**
	 * Keep the realm's store in sync with the auth token. Depends ONLY on
	 * token presence — `store.init` is idempotent per realm, so effect
	 * re-runs (navigation, remount) are no-ops while the socket is up. No
	 * cleanup teardown: the store owns the socket lifecycle (exactly one
	 * socket per realm, alive across navigations); `reset` runs only on
	 * logout (token → null) to close the socket and clear state.
	 */
	$effect(() => {
		const token = authStore.token;
		if (token) {
			store.init(fetch, token, realm);
		} else {
			store.reset();
		}
	});

	// Close the panel on outside click or Escape.
	$effect(() => {
		if (!open || !rootEl) return;
		/**
		 * @param {PointerEvent} event
		 */
		function onPointerDown(event) {
			const target = /** @type {Node|null} */ (event.target);
			if (target && rootEl && !rootEl.contains(target)) open = false;
		}
		/**
		 * @param {KeyboardEvent} event
		 */
		function onKeydown(event) {
			if (event.key === 'Escape') open = false;
		}
		document.addEventListener('pointerdown', onPointerDown);
		document.addEventListener('keydown', onKeydown);
		return () => {
			document.removeEventListener('pointerdown', onPointerDown);
			document.removeEventListener('keydown', onKeydown);
		};
	});

	/**
	 * Map a notification to its detail route (route template + params), or
	 * null when there is none.
	 * @param {import('$lib/api/notifications.js').NotificationItem} item
	 * @returns {{ route: string, params: Record<string, string> }|null}
	 */
	function routeFor(item) {
		const staff = realm !== 'client';
		if (!item.entity_id) return null;
		switch (item.entity_type) {
			case 'project':
				return {
					route: staff ? '/app/projects/[id]' : '/client/projects/[id]',
					params: { id: item.entity_id }
				};
			case 'invoice':
				return {
					route: staff ? '/app/invoices/[id]' : '/client/invoices/[id]',
					params: { id: item.entity_id }
				};
			case 'milestone': {
				const projectId = item.data?.project_id;
				return projectId
					? {
							route: staff ? '/app/projects/[id]' : '/client/projects/[id]',
							params: { id: String(projectId) }
						}
					: null;
			}
			default:
				return null;
		}
	}

	/**
	 * @param {import('$lib/api/notifications.js').NotificationItem} item
	 */
	async function handleClick(item) {
		store.markRead(item.id);
		const route = routeFor(item);
		if (route) {
			open = false;
			await goto(resolve(/** @type {any} */ (route.route), route.params));
		}
	}

	function handleMarkAllRead() {
		store.markAllRead();
	}
</script>

<div bind:this={rootEl} class="relative">
	<button
		type="button"
		onclick={() => (open = !open)}
		aria-label={store.unread > 0 ? `Notifications, ${store.unread} unread` : 'Notifications'}
		aria-haspopup="true"
		aria-expanded={open}
		class="relative inline-flex items-center justify-center rounded-md p-1.5 text-slate-600 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
	>
		<svg
			class="h-5 w-5"
			fill="none"
			viewBox="0 0 24 24"
			stroke-width="1.5"
			stroke="currentColor"
			aria-hidden="true"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
			/>
		</svg>
		{#if store.unread > 0}
			<span
				class="absolute top-0 right-0 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white"
				aria-hidden="true"
			>
				{store.unread > 99 ? '99+' : store.unread}
			</span>
		{/if}
	</button>

	{#if open}
		<!-- Mobile backdrop overlay (< sm) -->
		<button
			type="button"
			class="fixed inset-0 z-40 bg-black/20 sm:hidden"
			aria-label="Close notifications"
			onclick={() => (open = false)}
		></button>

		<div
			class="fixed inset-x-3 top-16 z-50 max-h-[calc(100vh-5rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl ring-1 ring-black/5 sm:absolute sm:inset-x-auto sm:top-full sm:right-0 sm:mt-2 sm:w-80 sm:max-h-[28rem] sm:max-w-[calc(100vw-2rem)] sm:rounded-xl"
			role="region"
			aria-label="Notifications"
		>
			<div class="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-4 py-3">
				<div class="flex items-center gap-2">
					<h3 class="text-sm font-semibold text-slate-900">Notifications</h3>
					{#if store.unread > 0}
						<span
							class="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-700"
						>
							{store.unread} new
						</span>
					{/if}
				</div>
				<div class="flex items-center gap-2">
					{#if store.unread > 0}
						<button
							type="button"
							onclick={handleMarkAllRead}
							class="rounded px-2 py-1 text-xs font-semibold text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
						>
							Mark all read
						</button>
					{/if}
					<button
						type="button"
						onclick={() => (open = false)}
						class="rounded-lg p-1 text-slate-400 hover:bg-slate-200/60 hover:text-slate-600 sm:hidden"
						aria-label="Close"
					>
						<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>
			<div class="max-h-[calc(100vh-10rem)] sm:max-h-96 overflow-y-auto divide-y divide-slate-100">
				{#if store.items.length === 0}
					<div class="px-4 py-10 text-center">
						<svg
							class="mx-auto h-8 w-8 text-slate-300"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="1.5"
								d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
							/>
						</svg>
						<p class="mt-2 text-sm font-medium text-slate-600">No notifications yet</p>
						<p class="mt-0.5 text-xs text-slate-400">We'll notify you when changes happen.</p>
					</div>
				{:else}
					<ul class="divide-y divide-slate-100">
						{#each store.items as item (item.id)}
							<li>
								<button
									type="button"
									onclick={() => handleClick(item)}
									aria-label={item.title || 'Notification'}
									class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none focus-visible:ring-inset {item.is_read
										? 'bg-white'
										: 'bg-indigo-50/30'}"
								>
									<span
										class="mt-1.5 h-2 w-2 shrink-0 rounded-full {item.is_read
											? 'bg-transparent'
											: 'bg-indigo-600'}"
										aria-hidden="true"
									></span>
									<span class="min-w-0 flex-1">
										<span
											class="block truncate text-sm {item.is_read
												? 'font-medium text-slate-700'
												: 'font-semibold text-slate-900'}"
										>
											{item.title || 'Notification'}
										</span>
										{#if item.body}
											<span class="mt-0.5 line-clamp-2 block text-xs text-slate-500"
												>{item.body}</span
											>
										{/if}
										<span class="mt-1 block text-[11px] text-slate-400"
											>{timeAgo(item.created_at)}</span
										>
									</span>
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>
	{/if}
</div>
