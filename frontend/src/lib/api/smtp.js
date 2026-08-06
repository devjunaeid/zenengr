import { apiFetch } from './client.js';

/**
 * Tenant SMTP configuration API endpoints (FEAT-013).
 */

/**
 * @typedef {object} SmtpConfig
 * @property {string} host
 * @property {number} port
 * @property {string|null} username null when no SMTP username is stored
 * @property {string} from_email
 * @property {string} from_name
 * @property {'none'|'starttls'|'ssl'} mode
 * @property {boolean} enabled
 * @property {boolean} has_password true when a password is stored server-side
 */

/**
 * @typedef {object} SmtpTestResult
 * @property {boolean} ok
 * @property {string} message
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<SmtpConfig>}
 */
export function getSmtpConfig(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/smtp-config', { token });
}

/**
 * Partial update. Omit `password` to keep the existing password; send a value
 * to rotate it. Send `username: null` to clear the username (also clears the
 * saved password), or `clear_password: true` to clear the stored password
 * while keeping the username. The backend returns the same shape as GET,
 * minus the password itself.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {Partial<Omit<SmtpConfig, 'has_password'>> & { password?: string; clear_password?: boolean }} payload
 * @returns {Promise<SmtpConfig>}
 */
export function updateSmtpConfig(fetchFn, token, payload) {
	return apiFetch(fetchFn, '/tenant/smtp-config', { method: 'PATCH', token, body: payload });
}

/**
 * Send a test email through the configured SMTP server. Without `toEmail` the
 * backend defaults to the configured `from_email`.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} [toEmail]
 * @returns {Promise<SmtpTestResult>}
 * @throws {ApiError} on send failure (e.g. 422 with the backend error message)
 */
export function testSmtpConfig(fetchFn, token, toEmail) {
	return apiFetch(fetchFn, '/tenant/smtp-config/test', {
		method: 'POST',
		token,
		body: toEmail ? { to_email: toEmail } : {}
	});
}
