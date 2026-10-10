import { apiFetch } from './client.js';

/**
 * Payments API client module (FEAT-027, TODO-227).
 *
 * Provides operations for recording project payments, invoice allocations,
 * voiding, restoring, and editing payment records.
 */

/**
 * Record a payment on a project with optional invoice allocations.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {object} payload
 * @param {string} payload.project_id
 * @param {number|string} payload.amount
 * @param {'cash'|'bank_transfer'|'cheque'|'card'|'other'} payload.method
 * @param {string} [payload.paid_on] ISO date string (YYYY-MM-DD)
 * @param {string} [payload.reference_note]
 * @param {string} [payload.notes]
 * @param {Array<{invoice_id: string, amount: number|string, line_item_id?: string}>} [payload.allocations]
 * @returns {Promise<any>}
 */
export async function recordPayment(fetchFn, token, payload) {
	return apiFetch(fetchFn, '/tenant/payments', {
		method: 'POST',
		token,
		body: payload
	});
}

/**
 * List payments recorded for a project.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {boolean} [includeVoided=true]
 * @returns {Promise<any[]>}
 */
export async function getProjectPayments(fetchFn, token, projectId, includeVoided = true) {
	return apiFetch(fetchFn, `/tenant/projects/${projectId}/payments`, {
		method: 'GET',
		token,
		params: { include_voided: includeVoided }
	});
}

/**
 * Fetch a specific payment by ID.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} paymentId
 * @returns {Promise<any>}
 */
export async function getPayment(fetchFn, token, paymentId) {
	return apiFetch(fetchFn, `/tenant/payments/${paymentId}`, {
		method: 'GET',
		token
	});
}

/**
 * Void a payment with an optional reason note.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} paymentId
 * @param {string} [reason]
 * @returns {Promise<any>}
 */
export async function voidPayment(fetchFn, token, paymentId, reason) {
	return apiFetch(fetchFn, `/tenant/payments/${paymentId}/void`, {
		method: 'POST',
		token,
		body: { reason }
	});
}

/**
 * Restore a previously voided payment.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} paymentId
 * @returns {Promise<any>}
 */
export async function restorePayment(fetchFn, token, paymentId) {
	return apiFetch(fetchFn, `/tenant/payments/${paymentId}/restore`, {
		method: 'POST',
		token
	});
}

/**
 * Update editable fields of a non-void payment.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} paymentId
 * @param {object} fields
 * @param {number|string} [fields.amount]
 * @param {string} [fields.paid_on]
 * @param {'cash'|'bank_transfer'|'cheque'|'card'|'other'} [fields.method]
 * @param {string} [fields.reference_note]
 * @param {string} [fields.notes]
 * @returns {Promise<any>}
 */
export async function updatePayment(fetchFn, token, paymentId, fields) {
	return apiFetch(fetchFn, `/tenant/payments/${paymentId}`, {
		method: 'PATCH',
		token,
		body: fields
	});
}
