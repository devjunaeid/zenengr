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
