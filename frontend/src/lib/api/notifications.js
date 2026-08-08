import { apiFetch, BASE_URL } from './client.js';

/**
 * Notifications API (FEAT-017). Staff endpoints live under /tenant/...,
 * client-portal endpoints under /client/...; both expose the same shapes.
 * Realtime delivery happens over a WebSocket (see stores/notifications.svelte.js).
 */

/**
 * @typedef {'admin'|'client'} NotificationRealm
 */

/**
 * @typedef {object} NotificationItem
 * @property {string} id
 * @property {string} event_type e.g. new_comment, invoice_issued
 * @property {string} title
 * @property {string} body
 * @property {string|null} entity_type 'project' | 'invoice' | 'milestone' | ...
 * @property {string|null} entity_id id of the referenced entity
 * @property {Record<string, any>|null} data free-form extras (e.g. milestone's project_id)
 * @property {string} created_at ISO timestamp
 * @property {boolean} [is_read] present on REST items; WS pushes omit it (treated unread)
 */

/**
 * @typedef {object} NotificationList
 * @property {NotificationItem[]} items newest first
 * @property {number} total
 * @property {number} unread
 * @property {number} page
 * @property {number} page_size
 */

/**
 * @param {NotificationRealm} realm
 * @returns {string} API path prefix for the realm
 */
function notificationsPath(realm) {
	return realm === 'client' ? '/client/notifications' : '/tenant/notifications';
}

/**
 * List notifications for the current user, newest first.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, unread_only?: boolean }} [params]
 * @param {NotificationRealm} [realm]
 * @returns {Promise<NotificationList>}
 */
export function listNotifications(fetchFn, token, params = {}, realm = 'admin') {
	return apiFetch(fetchFn, notificationsPath(realm), { token, params });
}

/**
 * Count of unread notifications.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {NotificationRealm} [realm]
 * @returns {Promise<{ count: number }>}
 */
export function unreadCount(fetchFn, token, realm = 'admin') {
	return apiFetch(fetchFn, `${notificationsPath(realm)}/unread-count`, { token });
}

/**
 * Mark a single notification as read. Returns null (204).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {NotificationRealm} [realm]
 * @returns {Promise<null>}
 */
export function markNotificationRead(fetchFn, token, id, realm = 'admin') {
	return apiFetch(fetchFn, `${notificationsPath(realm)}/${id}/read`, {
		method: 'POST',
		token
	});
}

/**
 * Mark all notifications as read. Returns null (204).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {NotificationRealm} [realm]
 * @returns {Promise<null>}
 */
export function markAllNotificationsRead(fetchFn, token, realm = 'admin') {
	return apiFetch(fetchFn, `${notificationsPath(realm)}/read-all`, { method: 'POST', token });
}

/**
 * Derive a WebSocket URL from BASE_URL for an API path, carrying the auth
 * token as a query param: 'http://localhost:8000/api/v1' + '/ws/admin' ->
 * 'ws://localhost:8000/api/v1/ws/admin?token=...'.
 * @param {string} path API path relative to /api/v1, e.g. '/ws/admin'
 * @param {string|null|undefined} [token]
 * @returns {string}
 */
export function wsUrl(path, token) {
	const base = BASE_URL.replace(/^http/, 'ws');
	const url = new URL(`${base}${path.startsWith('/') ? path : `/${path}`}`);
	if (token) url.searchParams.set('token', token);
	return url.toString();
}
