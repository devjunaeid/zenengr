import { browser } from '$app/environment';
import { SvelteMap } from 'svelte/reactivity';
import {
	listNotifications,
	markAllNotificationsRead,
	markNotificationRead,
	unreadCount,
	wsUrl
} from '$lib/api/notifications.js';

/**
 * Realtime notifications store (FEAT-017). One store instance per realm
 * (admin / client) so both sessions can coexist. Each instance keeps the
 * latest 50 items, an unread count, and a WebSocket connection to the
 * backend push endpoint with exponential reconnect backoff (2s doubling to
 * 30s max) plus a 30s keepalive ping while open.
 *
 * @typedef {import('$lib/api/notifications.js').NotificationRealm} NotificationRealm
 * @typedef {import('$lib/api/notifications.js').NotificationItem} NotificationItem
 */

const MAX_ITEMS = 50;
const PING_INTERVAL_MS = 30_000;
const MIN_RECONNECT_MS = 2_000;
const MAX_RECONNECT_MS = 30_000;

class NotificationStore {
	/** @type {NotificationRealm} */
	realm;
	/** @type {NotificationItem[]} newest first */
	items = $state([]);
	/** @type {number} */
	unread = $state(0);
	/** @type {'idle'|'connecting'|'open'|'closed'} */
	wsState = $state('idle');
	/** @type {boolean} */
	initialized = $state(false);

	/** @type {WebSocket|null} */
	#ws = null;
	/** @type {string|null} */
	#token = null;
	/** @type {number} */
	#reconnectDelay = MIN_RECONNECT_MS;
	/** @type {ReturnType<typeof setTimeout>|null} */
	#reconnectTimer = null;
	/** @type {ReturnType<typeof setInterval>|null} */
	#pingTimer = null;
	/** @type {boolean} */
	#closing = false;

	/**
	 * @param {NotificationRealm} realm
	 */
	constructor(realm) {
		this.realm = realm;
	}

	/**
	 * Fetch the initial list + unread count, then open the WebSocket.
	 * Idempotent for a given token; a changed token tears down and re-inits.
	 * @param {typeof fetch} fetchFn
	 * @param {string} token
	 * @param {NotificationRealm} realm
	 */
	async init(fetchFn, token, realm) {
		if (this.initialized && this.#token === token) return;
		if (this.initialized) this.reset();
		this.#token = token;
		try {
			const [list, count] = await Promise.all([
				listNotifications(fetchFn, token, { page: 1, page_size: 20 }, realm),
				unreadCount(fetchFn, token, realm)
			]);
			// Torn down (logout / token change) while the fetch was in flight.
			if (this.#token !== token) return;
			this.items = list?.items ?? [];
			this.unread = count?.count ?? list?.unread ?? 0;
		} catch {
			// Initial fetch failed (offline / 401) — still attempt the socket;
			// items then arrive from pushes once it opens.
		}
		this.initialized = true;
		this.#connect(fetchFn, realm);
	}

	/**
	 * Full teardown: close socket, cancel timers, clear state. Called on
	 * logout and when the token changes.
	 */
	reset() {
		this.#closing = true;
		this.#closeSocket();
		this.#stopPing();
		this.#stopReconnectTimer();
		this.items = [];
		this.unread = 0;
		this.wsState = 'idle';
		this.initialized = false;
		this.#token = null;
		this.#reconnectDelay = MIN_RECONNECT_MS;
		this.#closing = false;
	}

	/**
	 * Optimistically mark a single notification read, then confirm with the API.
	 * @param {string} id
	 */
	async markRead(id) {
		const item = this.items.find((n) => n.id === id);
		if (!item || item.is_read) return;
		item.is_read = true;
		this.unread = Math.max(0, this.unread - 1);
		try {
			await markNotificationRead(fetch, /** @type {string} */ (this.#token), id, this.realm);
		} catch {
			// Optimistic; the backend reconciles on the next full fetch.
		}
	}

	/**
	 * Optimistically mark every notification read, then confirm with the API.
	 */
	async markAllRead() {
		if (this.unread === 0) return;
		this.unread = 0;
		for (const n of this.items) n.is_read = true;
		try {
			await markAllNotificationsRead(fetch, /** @type {string} */ (this.#token), this.realm);
		} catch {
			// Optimistic; ignored.
		}
	}

	/**
	 * @param {typeof fetch} fetchFn
	 * @param {NotificationRealm} realm
	 */
	#connect(fetchFn, realm) {
		this.#closeSocket();
		this.#stopReconnectTimer();
		if (!browser) return;
		this.wsState = 'connecting';
		/** @type {WebSocket} */
		let ws;
		try {
			ws = new WebSocket(wsUrl(`/ws/${realm === 'client' ? 'client' : 'admin'}`, this.#token));
		} catch {
			this.#scheduleReconnect(fetchFn, realm);
			return;
		}
		this.#ws = ws;

		ws.onopen = () => {
			if (this.#ws !== ws) return;
			this.wsState = 'open';
			this.#reconnectDelay = MIN_RECONNECT_MS;
			this.#startPing();
		};

		ws.onmessage = (event) => {
			if (this.#ws !== ws) return;
			try {
				const msg = JSON.parse(String(event.data));
				if (msg && typeof msg.id === 'string' && msg.event_type) {
					this.#pushItem(/** @type {NotificationItem} */ (msg));
				}
			} catch {
				// Malformed frame — ignore.
			}
		};

		ws.onclose = () => {
			if (this.#ws !== ws) return;
			this.wsState = 'closed';
			this.#stopPing();
			if (this.#closing) return;
			this.#scheduleReconnect(fetchFn, realm);
		};

		ws.onerror = () => {
			if (this.#ws === ws) ws.close();
		};
	}

	/**
	 * @param {typeof fetch} fetchFn
	 * @param {NotificationRealm} realm
	 */
	#scheduleReconnect(fetchFn, realm) {
		this.#stopReconnectTimer();
		this.#reconnectTimer = setTimeout(() => {
			this.#connect(fetchFn, realm);
		}, this.#reconnectDelay);
		this.#reconnectDelay = Math.min(this.#reconnectDelay * 2, MAX_RECONNECT_MS);
	}

	/**
	 * Insert a pushed notification at the front (dedup by id, cap at MAX_ITEMS).
	 * @param {NotificationItem} item
	 */
	#pushItem(item) {
		const existing = this.items.find((n) => n.id === item.id);
		if (existing) {
			this.items[this.items.indexOf(existing)] = item;
			return;
		}
		this.items = [item, ...this.items].slice(0, MAX_ITEMS);
		if (!item.is_read) this.unread += 1;
	}

	#startPing() {
		this.#stopPing();
		this.#pingTimer = setInterval(() => {
			if (this.#ws && this.#ws.readyState === WebSocket.OPEN) {
				this.#ws.send('ping');
			}
		}, PING_INTERVAL_MS);
	}

	#stopPing() {
		if (this.#pingTimer !== null) {
			clearInterval(this.#pingTimer);
			this.#pingTimer = null;
		}
	}

	#stopReconnectTimer() {
		if (this.#reconnectTimer !== null) {
			clearTimeout(this.#reconnectTimer);
			this.#reconnectTimer = null;
		}
	}

	#closeSocket() {
		if (this.#ws) {
			try {
				this.#ws.onclose = null;
				this.#ws.close();
			} catch {
				// Already closed.
			}
			this.#ws = null;
		}
	}
}

/**
 * One store instance per realm, pre-seeded at module load so the `realm`
 * accessor only ever READS the map. Never mutate this map lazily — callers
 * may access it from `$derived`/render context, and a lazy `set` there
 * triggers the Svelte 5 `state_unsafe_mutation` error.
 * @type {SvelteMap<NotificationRealm, NotificationStore>}
 */
const stores = new SvelteMap([
	['admin', new NotificationStore('admin')],
	['client', new NotificationStore('client')]
]);

export const notifications = {
	/**
	 * Get the store for a realm. Pure read — both realms are pre-seeded, so
	 * this is safe to call from `$derived`/template context.
	 * @param {NotificationRealm} realm
	 * @returns {NotificationStore}
	 */
	realm(realm) {
		const store = stores.get(realm);
		if (!store) {
			throw new Error(`Unknown notification realm: ${realm}`);
		}
		return store;
	},

	/**
	 * Teardown for a realm (logout / token change). Safe to call anytime.
	 * @param {NotificationRealm} realm
	 */
	reset(realm) {
		stores.get(realm)?.reset();
	}
};
