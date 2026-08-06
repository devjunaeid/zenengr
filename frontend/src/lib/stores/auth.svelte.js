import { browser } from '$app/environment';
import * as authApi from '$lib/api/auth.js';

const TOKEN_KEY = 'zenengr.token';

/** @type {import('$lib/api/auth.js').AuthUser|null} */
let user = $state(null);
/**
 * Granted permissions as "action.resource" strings. Null when the backend
 * session lacks a permissions list (legacy role-based backend).
 * @type {Set<string>|null}
 */
let perms = $state(null);
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
	 * Permission check for the staff session. Admin and super_admin bypass
	 * everything. When the session carries no `permissions` list (legacy
	 * backend), fall back to role-based approximation: managers may 'manage',
	 * everyone else cannot — mirrors the old admin/manager manage gate so
	 * pages don't flash-denied during the parallel backend change.
	 * @param {string} action
	 * @param {string} resource
	 * @returns {boolean}
	 */
	can(action, resource) {
		const u = user;
		if (!u) return false;
		const r = u.role;
		if (r === 'super_admin' || r === 'admin') return true;
		if (Array.isArray(u.permissions)) {
			return perms?.has(`${action}.${resource}`) ?? false;
		}
		// Legacy fallback (permissions missing from the session).
		return r === 'manager' && action === 'manage';
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
		setUser(res.user);
		initialized = true;
		if (browser) localStorage.setItem(TOKEN_KEY, res.access_token);
		return res.user;
	},

	/**
	 * Register from an invite (auto-login). LoginResponse already carries the
	 * full user, so no extra /auth/me fetch is needed.
	 * @param {typeof fetch} fetchFn
	 * @param {{ token: string, full_name: string, password: string }} payload
	 * @returns {Promise<import('$lib/api/auth.js').AuthUser>}
	 */
	async register(fetchFn, payload) {
		const res = await authApi.register(fetchFn, payload);
		token = res.access_token;
		setUser(res.user);
		initialized = true;
		if (browser) localStorage.setItem(TOKEN_KEY, res.access_token);
		return res.user;
	},

	logout() {
		user = null;
		perms = null;
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
			setUser(await authApi.me(fetchFn, saved));
			token = saved;
		} catch {
			if (browser) localStorage.removeItem(TOKEN_KEY);
		}
	}
	initialized = true;
}

/**
 * Set the current user and normalize its permission list into a reactive Set.
 * @param {import('$lib/api/auth.js').AuthUser} u
 */
function setUser(u) {
	user = u;
	perms = Array.isArray(u.permissions) ? new Set(u.permissions) : null;
}

/**
 * Home route for a staff role.
 * @param {string|null|undefined} role
 */
export function homeForRole(role) {
	return role === 'super_admin' ? '/admin' : '/app';
}
