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
		<div
			class="absolute right-0 z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-lg bg-slate-100 shadow-lg ring-1 ring-slate-200"
			role="region"
			aria-label="Notifications"
		>
			<div class="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
				<h3 class="text-sm font-semibold text-slate-900">Notifications</h3>
				{#if store.unread > 0}
					<button
						type="button"
						onclick={handleMarkAllRead}
						class="rounded text-xs font-medium text-indigo-600 hover:text-indigo-800 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Mark all read
					</button>
				{/if}
			</div>
			<div class="max-h-96 overflow-y-auto">
				{#if store.items.length === 0}
					<p class="px-4 py-8 text-center text-sm text-slate-500">No notifications yet.</p>
				{:else}
					<ul class="divide-y divide-slate-200">
						{#each store.items as item (item.id)}
							<li>
								<button
									type="button"
									onclick={() => handleClick(item)}
									aria-label={item.title || 'Notification'}
									class="flex w-full items-start gap-2.5 px-4 py-3 text-left hover:bg-slate-200/70 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none focus-visible:ring-inset"
								>
									<span
										class="mt-1.5 h-2 w-2 shrink-0 rounded-full {item.is_read
											? 'bg-transparent'
											: 'bg-indigo-500'}"
										aria-hidden="true"
									></span>
									<span class="min-w-0 flex-1">
										<span
											class="block truncate text-sm {item.is_read
												? 'font-medium text-slate-600'
												: 'font-semibold text-slate-900'}"
										>
											{item.title || 'Notification'}
										</span>
										{#if item.body}
											<span class="mt-0.5 line-clamp-2 block text-sm text-slate-500"
												>{item.body}</span
											>
										{/if}
										<span class="mt-0.5 block text-xs text-slate-400"
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
