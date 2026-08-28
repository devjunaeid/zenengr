import { browser } from '$app/environment';
import * as portalApi from '$lib/api/portal.js';

const TOKEN_KEY = 'zenengr.portal_token';

/** @type {import('$lib/api/portal.js').PortalUser|null} */
let user = $state(null);
/** @type {import('$lib/api/portal.js').PortalClient|null} */
let client = $state(null);
/** @type {string|null} */
let tenantName = $state('');
/** @type {string|null} */
let tenantLogoUrl = $state(null);
/** @type {string|null} */
let token = $state(null);
let initialized = $state(false);

/** @type {Promise<void>|null} */
let initPromise = null;

/**
 * Runes-based auth store for the client-realm session.
 * Uses a separate localStorage key from the staff store so both
 * sessions can coexist in the same browser.
 */
export const portalAuth = {
	get user() {
		return user;
	},
	get client() {
		return client;
	},
	get tenantName() {
		return tenantName;
	},
	get tenantLogoUrl() {
		return tenantLogoUrl;
	},
	get token() {
		return token;
	},
	get initialized() {
		return initialized;
	},
	get isClientUser() {
		return user?.role === 'client_user';
	},

	/**
	 * Restore the session once. Idempotent.
	 * @param {typeof fetch} [fetchFn]
	 */
	async init(fetchFn = fetch) {
		if (initialized) return;
		if (!initPromise) initPromise = restore(fetchFn);
		await initPromise;
	},

	/**
	 * Log in. Returns user on success.
	 * @param {typeof fetch} fetchFn
	 * @param {string} email
	 * @param {string} password
	 * @returns {Promise<import('$lib/api/portal.js').PortalUser>}
	 */
	async login(fetchFn, email, password) {
		const res = await portalApi.login(fetchFn, email, password);
		token = res.access_token;
		user = res.user;
		// Fetch full client details after login
		const me = await portalApi.me(fetchFn, res.access_token);
		client = me.client;
		tenantName = me.tenant_name ?? '';
		tenantLogoUrl = me.tenant_logo_url ?? null;
		user = me;
		initialized = true;
		if (browser) localStorage.setItem(TOKEN_KEY, res.access_token);
		return res.user;
	},

	/**
	 * Register from an invite (auto-login).
	 * @param {typeof fetch} fetchFn
	 * @param {{ token: string, full_name: string, password: string }} payload
	 * @returns {Promise<import('$lib/api/portal.js').PortalUser>}
	 */
	async register(fetchFn, payload) {
		const res = await portalApi.register(fetchFn, payload);
		token = res.access_token;
		const me = await portalApi.me(fetchFn, res.access_token);
		client = me.client;
		tenantName = me.tenant_name ?? '';
		tenantLogoUrl = me.tenant_logo_url ?? null;
		user = me;
		initialized = true;
		if (browser) localStorage.setItem(TOKEN_KEY, res.access_token);
		return res.user;
	},

	logout() {
		user = null;
		client = null;
		tenantName = '';
		tenantLogoUrl = null;
		token = null;
		if (browser) localStorage.removeItem(TOKEN_KEY);
	}
};

/**
 * @param {typeof fetch} fetchFn
 */
async function restore(fetchFn) {
	const saved = browser ? localStorage.getItem(TOKEN_KEY) : null;
	if (saved) {
		try {
			const me = await portalApi.me(fetchFn, saved);
			user = me;
			client = me.client;
			tenantName = me.tenant_name ?? '';
			tenantLogoUrl = me.tenant_logo_url ?? null;
			token = saved;
		} catch {
			if (browser) localStorage.removeItem(TOKEN_KEY);
		}
	}
	initialized = true;
}
