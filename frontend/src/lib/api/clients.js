import { apiFetch } from './client.js';

/**
 * Tenant client-management API endpoints.
 *
 * GET endpoints (`listClients`, `listTags`, `getClient`, `listNotes`, `listActivity`)
 * are accessible to all staff roles (admin, manager, employee).
 *
 * Write endpoints (`createClient`, `updateClient`, `archiveClient`,
 * `unarchiveClient`, `addNote`) require admin or manager. The server enforces
 * permissions; the UI mirrors this with read-only views for employees.
 */

/**
 * @typedef {object} ClientListItem
 * @property {string} id
 * @property {string} name
 * @property {'company'|'individual'} client_type
 * @property {string|null} email
 * @property {string|null} phone
 * @property {'active'|'archived'} status
 * @property {string[]} tags
 * @property {string} created_at
 * @property {string} updated_at
 * @property {number} active_projects
 * @property {number} total_invoiced
 * @property {number} total_outstanding
 */

/**
 * @typedef {object} ClientUserSummary
 * @property {string} id
 * @property {string} email
 * @property {string|null} full_name
 * @property {boolean} is_active
 * @property {boolean} is_primary_billing_contact
 */

/**
 * @typedef {object} ClientActivityEntry
 * @property {string} id
 * @property {string} action
 * @property {string} entity_type
 * @property {string|null} entity_id
 * @property {Record<string, any>} details
 * @property {string|null} actor_id
 * @property {string} actor_type
 * @property {string} created_at
 */

/**
 * @typedef {object} LedgerEntry
 * @property {string} id
 * @property {'payment'|'refund'|'advance_received'|'advance_applied'} kind
 * @property {string} amount signed decimal-as-string (refunds/advance receipts negative)
 * @property {string} reference reference note, may be empty
 * @property {string|null} invoice_id
 * @property {string} created_at ISO datetime
 * @property {string} running_balance decimal-as-string
 */

/**
 * @typedef {object} ClientLedgerResponse
 * @property {string} advance_balance decimal-as-string
 * @property {LedgerEntry[]} entries chronological, oldest first
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, status?: string, q?: string, tag?: string, sort?: string }} [params]
 * @returns {Promise<{ items: ClientListItem[], total: number, page: number, page_size: number }>}
 */
export function listClients(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/tenant/clients', { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<{ tags: string[] }>}
 */
export function listTags(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/clients/tags', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<ClientListItem & { tenant_id: string, billing_address: string|null, tax_id: string|null, client_users: ClientUserSummary[], recent_activity: ClientActivityEntry[] }>}
 */
export function getClient(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(id)}`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ name: string, client_type: 'company'|'individual', email?: string, phone?: string, billing_address?: string, tax_id?: string, tags?: string[] }} body
 * @returns {Promise<ClientListItem>}
 */
export function createClient(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/clients', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {Record<string, any>} body partial fields (status is immutable)
 * @returns {Promise<ClientListItem>}
 */
export function updateClient(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(id)}`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<{ id: string, name: string, status: 'archived' }>}
 */
export function archiveClient(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(id)}/archive`, {
		method: 'POST',
		token
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<{ id: string, name: string, status: 'active' }>}
 */
export function unarchiveClient(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(id)}/unarchive`, {
		method: 'POST',
		token
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ page?: number, page_size?: number }} [params]
 * @returns {Promise<{ items: Array<{ id: string, body: string, author_id: string|null, created_at: string }>, total: number, page: number, page_size: number }>}
 */
export function listNotes(fetchFn, token, id, params = {}) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(id)}/notes`, { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ body: string }} body
 */
export function addNote(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(id)}/notes`, {
		method: 'POST',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ page?: number, page_size?: number }} [params]
 * @returns {Promise<{ items: ClientActivityEntry[], total: number, page: number, page_size: number }>}
 */
export function listActivity(fetchFn, token, id, params = {}) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(id)}/activity`, {
		token,
		params
	});
}

/**
 * Client ledger: advance balance + signed money entries (payments, refunds,
 * advance receipts, advance applications) with running balance.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} clientId
 * @returns {Promise<ClientLedgerResponse>}
 */
export function getClientLedger(fetchFn, token, clientId) {
	return apiFetch(fetchFn, `/tenant/clients/${encodeURIComponent(clientId)}/ledger`, { token });
}
