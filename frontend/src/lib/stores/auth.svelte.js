import { browser } from '$app/environment';
import * as authApi from '$lib/api/auth.js';

const TOKEN_KEY = 'zenengr.token';

/** @type {import('$lib/api/auth.js').AuthUser|null} */
let user = $state(null);
/** @type {string|null} */
let token = $state(null);
let initialized = $state(false);

/** @type {Promise<void>|null} */
let initPromise = null;

/**
 * Runes-based auth store for the staff (admin-realm) session.
 * Token persists in localStorage; init() restores the session via /auth/me.
 */
export const auth = {
	get user() {
		return user;
	},
	get token() {
		return token;
	},
	get initialized() {
		return initialized;
	},
	get isSuperAdmin() {
		return user?.role === 'super_admin';
	},
	get isTenantAdmin() {
		return user?.role === 'admin';
	},
	get home() {
		return homeForRole(user?.role);
	},

	/**
	 * Restore the session once. Idempotent; safe to call from every guard.
	 * @param {typeof fetch} [fetchFn]
	 */
	async init(fetchFn = fetch) {
		if (initialized) return;
		if (!initPromise) initPromise = restore(fetchFn);
		await initPromise;
	},

	/**
	 * Log in with email/password. Returns the user on success.
	 * @param {typeof fetch} fetchFn
	 * @param {string} email
	 * @param {string} password
	 * @returns {Promise<import('$lib/api/auth.js').AuthUser>}
	 */
	async login(fetchFn, email, password) {
		const res = await authApi.login(fetchFn, email, password);
		token = res.access_token;
		user = res.user;
		initialized = true;
		if (browser) localStorage.setItem(TOKEN_KEY, res.access_token);
		return res.user;
	},

	logout() {
		user = null;
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
			user = await authApi.me(fetchFn, saved);
			token = saved;
		} catch {
			if (browser) localStorage.removeItem(TOKEN_KEY);
		}
	}
	initialized = true;
}

/**
 * Home route for a staff role.
 * @param {string|null|undefined} role
 */
export function homeForRole(role) {
	return role === 'super_admin' ? '/admin' : '/app';
}
