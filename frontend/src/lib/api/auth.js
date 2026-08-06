import { apiFetch } from './client.js';

/**
 * @typedef {object} AuthUser
 * @property {string} id
 * @property {string} email
 * @property {string} full_name
 * @property {'super_admin'|'admin'|'manager'|'employee'} role
 * @property {string|null} tenant_id
 */

/**
 * Staff login (admin realm: super_admin, admin, manager, employee).
 * @param {typeof fetch} fetchFn
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ access_token: string, token_type: string, user: AuthUser }>}
 */
export function login(fetchFn, email, password) {
	return apiFetch(fetchFn, '/auth/login', { method: 'POST', body: { email, password } });
}

/**
 * Fetch the currently authenticated user.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<AuthUser>}
 */
export function me(fetchFn, token) {
	return apiFetch(fetchFn, '/auth/me', { token });
}

/**
 * @typedef {object} InviteLookup
 * @property {string} email
 * @property {'admin'|'manager'|'employee'} role
 * @property {string} tenant_name
 * @property {string} expires_at
 */

/**
 * Fetch staff invite details by token (public, no auth).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<InviteLookup>}
 */
export function getInvite(fetchFn, token) {
	return apiFetch(fetchFn, `/auth/invite/${encodeURIComponent(token)}`);
}

/**
 * Register from a staff invite (public, auto-login).
 * @param {typeof fetch} fetchFn
 * @param {{ token: string, full_name: string, password: string }} payload
 * @returns {Promise<{ access_token: string, token_type: string, user: AuthUser }>}
 */
export function register(fetchFn, payload) {
	return apiFetch(fetchFn, '/auth/register', { method: 'POST', body: payload });
}
