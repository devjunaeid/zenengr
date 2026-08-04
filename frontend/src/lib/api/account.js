import { apiFetch } from './client.js';

/**
 * Account self-service API (FEAT-011): profile, password, notification
 * preferences, activity history, and password reset. Each function takes a
 * `realm` option selecting the staff (`admin`) or client portal variant.
 */

/**
 * @typedef {'admin'|'client'} AccountRealm
 */

/**
 * @typedef {object} AccountProfile
 * @property {string} id
 * @property {string} email
 * @property {string} full_name
 * @property {string} role
 * @property {string|null} tenant_id
 * @property {string|null} avatar_url
 * @property {string|null} phone
 * @property {string|null} timezone
 * @property {string|null} language
 * @property {string|null} pending_email
 */

/**
 * @typedef {object} ActivityEntry
 * @property {string} id
 * @property {string} event_type
 * @property {string} description
 * @property {string|null} old_value
 * @property {string|null} new_value
 * @property {string} created_at
 */

/**
 * @typedef {object} NotificationPreference
 * @property {string} event_type
 * @property {boolean} enabled
 */

/**
 * @typedef {object} RealmOptions
 * @property {AccountRealm} [realm]
 */

/**
 * @param {AccountRealm} realm
 */
function profilePath(realm) {
	return realm === 'client' ? '/client/auth/user-profile' : '/auth/profile';
}

/**
 * @param {AccountRealm} realm
 */
function changePasswordPath(realm) {
	return realm === 'client' ? '/client/auth/change-password' : '/auth/change-password';
}

/**
 * @param {AccountRealm} realm
 */
function activityPath(realm) {
	return realm === 'client' ? '/client/auth/activity' : '/auth/activity';
}

/**
 * @param {AccountRealm} realm
 */
function preferencesPath(realm) {
	return realm === 'client'
		? '/client/auth/notification-preferences'
		: '/auth/notification-preferences';
}

/**
 * @param {AccountRealm} realm
 */
function forgotPasswordPath(realm) {
	return realm === 'client' ? '/client/auth/forgot-password' : '/auth/forgot-password';
}

/**
 * @param {AccountRealm} realm
 */
function resetPasswordPath(realm) {
	return realm === 'client' ? '/client/auth/reset-password' : '/auth/reset-password';
}

/**
 * @param {AccountRealm} realm
 */
function mePath(realm) {
	return realm === 'client' ? '/client/auth/me' : '/auth/me';
}

/**
 * Fetch the current user's full profile (includes phone, timezone, language,
 * avatar_url, pending_email beyond the login store's summary).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {RealmOptions} [options]
 * @returns {Promise<AccountProfile>}
 */
export function getMe(fetchFn, token, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, mePath(realm), { token });
}

/**
 * @typedef {object} ProfileUpdatePayload
 * @property {string} [full_name]
 * @property {string|null} [avatar_url]
 * @property {string|null} [phone]
 * @property {string|null} [timezone]
 * @property {string|null} [language]
 * @property {string} [email]
 */

/**
 * Update the current user's own profile fields.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {ProfileUpdatePayload} payload
 * @param {RealmOptions} [options]
 * @returns {Promise<AccountProfile>}
 */
export function updateProfile(fetchFn, token, payload, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, profilePath(realm), { method: 'PATCH', token, body: payload });
}

/**
 * Change the current user's password (server enforces tenant policy, min 8).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ current_password: string, new_password: string }} payload
 * @param {RealmOptions} [options]
 * @returns {Promise<{ status: string }>}
 */
export function changePassword(fetchFn, token, payload, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, changePasswordPath(realm), { method: 'POST', token, body: payload });
}

/**
 * List the current user's activity history, newest first.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {RealmOptions} [options]
 * @returns {Promise<ActivityEntry[]>}
 */
export function getActivity(fetchFn, token, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, activityPath(realm), { token });
}

/**
 * List the current user's per-event notification preferences.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {RealmOptions} [options]
 * @returns {Promise<NotificationPreference[]>}
 */
export function getNotificationPreferences(fetchFn, token, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, preferencesPath(realm), { token });
}

/**
 * Upsert notification preferences. Backend upserts, so sending a single
 * preference is fine for per-toggle saves.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ preferences: NotificationPreference[] }} payload
 * @param {RealmOptions} [options]
 * @returns {Promise<NotificationPreference[]>}
 */
export function updateNotificationPreferences(fetchFn, token, payload, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, preferencesPath(realm), { method: 'PATCH', token, body: payload });
}

/**
 * Public: request a password reset email. Always succeeds (no existence leak).
 * @param {typeof fetch} fetchFn
 * @param {string} email
 * @param {RealmOptions} [options]
 * @returns {Promise<{ status: string }>}
 */
export function forgotPassword(fetchFn, email, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, forgotPasswordPath(realm), { method: 'POST', body: { email } });
}

/**
 * Public: consume a password reset token and set a new password.
 * @param {typeof fetch} fetchFn
 * @param {{ token: string, new_password: string }} payload
 * @param {RealmOptions} [options]
 * @returns {Promise<{ status: string }>}
 */
export function resetPassword(fetchFn, payload, options = {}) {
	const { realm = 'admin' } = options;
	return apiFetch(fetchFn, resetPasswordPath(realm), { method: 'POST', body: payload });
}
