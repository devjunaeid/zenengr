import { apiFetch } from './client.js';

/**
 * Tenant staff API endpoints (admin / manager / employee roles).
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 */
export function getProfile(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/profile', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ business_name?: string, contact_info?: Record<string, any>, branding?: Record<string, any> }} body
 */
export function updateProfile(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/profile', { method: 'PATCH', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<Array<{ key: string, value: string|null, permission_level: string, editable: boolean }>>}
 */
export function getSettings(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/settings', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} key
 * @param {string} value
 */
export function updateSetting(fetchFn, token, key, value) {
	return apiFetch(fetchFn, `/tenant/settings/${encodeURIComponent(key)}`, {
		method: 'PATCH',
		token,
		body: { value }
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<{ plan_name: string, limits: Record<string, number>, usage: Record<string, number> }>}
 */
export function getPlan(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/plan', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<Array<{ key: string, enabled: boolean }>>}
 */
export function getFlags(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/flags', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, is_active?: boolean, role?: string }} [params]
 * @returns {Promise<{ items: Array<{ id: string, email: string, full_name: string, role: string, is_active: boolean, created_at: string }>, total: number, page: number, page_size: number }>}
 */
export function listUsers(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/tenant/users', { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ email: string, role: 'admin'|'manager'|'employee' }} body
 */
export function createInvite(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/invites', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<Array<{ id: string, email: string, role: string, expires_at: string, accepted_at: string|null, status: string }>>}
 */
export function listInvites(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/invites', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} inviteId
 */
export function deleteInvite(fetchFn, token, inviteId) {
	return apiFetch(fetchFn, `/tenant/invites/${inviteId}`, { method: 'DELETE', token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} userId
 * @param {'admin'|'manager'|'employee'} role
 */
export function changeRole(fetchFn, token, userId, role) {
	return apiFetch(fetchFn, `/tenant/users/${userId}/role`, {
		method: 'PATCH',
		token,
		body: { role }
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} userId
 * @param {'deactivate'|'reactivate'} action
 */
export function setUserActive(fetchFn, token, userId, action) {
	return apiFetch(fetchFn, `/tenant/users/${userId}/${action}`, { method: 'POST', token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, action?: string, from?: string, to?: string }} [params]
 * @returns {Promise<{ items: Array<{ id: string, action: string, actor_id: string, actor_type: string, entity_type: string, entity_id: string|null, details: Record<string, any>, created_at: string }>, total: number, page: number, page_size: number }>}
 */
export function getAuditLogs(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/tenant/audit-logs', { token, params });
}
