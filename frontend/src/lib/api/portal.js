import { apiFetch } from './client.js';

/**
 * @typedef {object} PortalUser
 * @property {string} id
 * @property {string} email
 * @property {string} full_name
 * @property {'client_user'} role
 * @property {string} client_id
 * @property {string} tenant_id
 */

/**
 * @typedef {object} PortalClient
 * @property {string} id
 * @property {string} name
 * @property {string} status
 * @property {string|null} email
 * @property {string|null} phone
 * @property {Record<string,any>|null} billing_address
 * @property {string|null} tax_id
 */

/**
 * @typedef {{ access_token: string, token_type: string, user: PortalUser }} LoginResponse
 */

/**
 * Client login.
 * @param {typeof fetch} fetchFn
 * @param {string} email
 * @param {string} password
 * @returns {Promise<LoginResponse>}
 */
export function login(fetchFn, email, password) {
	return apiFetch(fetchFn, '/client/auth/login', { method: 'POST', body: { email, password } });
}

/**
 * Fetch current client user + client details.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<{ user: PortalUser, client: PortalClient, tenant_name?: string }>}
 */
export function me(fetchFn, token) {
	return apiFetch(fetchFn, '/client/auth/me', { token });
}

/**
 * Update client contact fields (email, phone).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ email?: string, phone?: string }} fields
 * @returns {Promise<any>}
 */
export function updateProfile(fetchFn, token, fields) {
	return apiFetch(fetchFn, '/client/auth/profile', { method: 'PATCH', token, body: fields });
}

/**
 * Fetch invite details by token.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<{ email: string, client_name: string, tenant_name: string, expires_at: string }>}
 */
export function getInvite(fetchFn, token) {
	return apiFetch(fetchFn, `/client/auth/invite/${encodeURIComponent(token)}`);
}

/**
 * Register from an invite.
 * @param {typeof fetch} fetchFn
 * @param {{ token: string, full_name: string, password: string }} payload
 * @returns {Promise<LoginResponse>}
 */
export function register(fetchFn, payload) {
	return apiFetch(fetchFn, '/client/auth/register', { method: 'POST', body: payload });
}
