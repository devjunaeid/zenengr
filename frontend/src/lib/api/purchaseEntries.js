import { apiFetch } from './client.js';

/**
 * Purchase Entry API helpers.
 *
 * Standalone module — no connection to the Invoice system.
 * All endpoints are scoped to /tenant/projects/{projectId}/purchase-entries.
 */

/**
 * @typedef {object} PurchaseEntryItem
 * @property {string} id
 * @property {string|null} item_date ISO date or null
 * @property {string} description
 * @property {string} quantity decimal-as-string
 * @property {string} rate decimal-as-string
 * @property {string} total decimal-as-string (quantity × rate)
 */

/**
 * @typedef {object} PurchaseEntry
 * @property {string} id
 * @property {string} project_id
 * @property {string} title
 * @property {string} notes
 * @property {string|null} entry_date ISO date or null
 * @property {string} grand_total decimal-as-string
 * @property {string|null} created_by_id
 * @property {PurchaseEntryItem[]} items
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {object} PurchaseEntryListItem
 * @property {string} id
 * @property {string} project_id
 * @property {string} title
 * @property {string|null} entry_date ISO date or null
 * @property {string} grand_total decimal-as-string
 * @property {number} item_count
 * @property {string} created_at
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {{ page?: number, page_size?: number }} [params]
 * @returns {Promise<{ items: PurchaseEntryListItem[], total: number, page: number, page_size: number }>}
 */
export function listPurchaseEntries(fetchFn, token, projectId, params = {}) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/purchase-entries`,
		{ token, params }
	);
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {string} entryId
 * @returns {Promise<PurchaseEntry>}
 */
export function getPurchaseEntry(fetchFn, token, projectId, entryId) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/purchase-entries/${encodeURIComponent(entryId)}`,
		{ token }
	);
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {{
 *   title?: string,
 *   notes?: string,
 *   entry_date?: string,
 *   items: Array<{ item_date?: string, description: string, quantity: number|string, rate: number|string }>
 * }} body
 * @returns {Promise<PurchaseEntry>}
 */
export function createPurchaseEntry(fetchFn, token, projectId, body) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/purchase-entries`,
		{ method: 'POST', token, body }
	);
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {string} entryId
 * @param {Record<string, any>} body partial fields (title, notes, entry_date, items)
 * @returns {Promise<PurchaseEntry>}
 */
export function updatePurchaseEntry(fetchFn, token, projectId, entryId, body) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/purchase-entries/${encodeURIComponent(entryId)}`,
		{ method: 'PATCH', token, body }
	);
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {string} entryId
 * @returns {Promise<null>}
 */
export function deletePurchaseEntry(fetchFn, token, projectId, entryId) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/purchase-entries/${encodeURIComponent(entryId)}`,
		{ method: 'DELETE', token }
	);
}
