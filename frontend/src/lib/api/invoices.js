import { ApiError, apiFetch, BASE_URL } from './client.js';

/**
 * Tenant invoicing API endpoints (FR-7.6).
 *
 * Accessible to all staff (admin, manager, employee) for reads and
 * create/update on draft invoices; issuing and voiding are server-enforced.
 */

/**
 * @typedef {object} InvoiceListItem
 * @property {string} id
 * @property {string|null} invoice_number null while draft
 * @property {'draft'|'issued'|'partially_paid'|'paid'|'void'} status
 * @property {string|null} project_id null for general (internal) invoices
 * @property {string|null} client_id null for general (internal) invoices
 * @property {string|null} issue_date ISO date
 * @property {string|null} due_date ISO date
 * @property {number|string} total decimal-as-string or number
 * @property {string} created_at
 */

/**
 * @typedef {object} InvoiceLineItem
 * @property {string} id
 * @property {string} description
 * @property {number} quantity
 * @property {number|string} unit_price decimal-as-string or number
 * @property {number|string} amount decimal-as-string or number
 * @property {string|null} entry_date ISO date the item was delivered/performed; null when unset
 * @property {string|null} service_id
 * @property {string|null} project_service_id null for custom lines
 */

/**
 * @typedef {object} InvoiceDetailResponse
 * @property {string} id
 * @property {string|null} invoice_number null while draft
 * @property {'draft'|'issued'|'partially_paid'|'paid'|'void'} status
 * @property {string|null} project_id null for general (internal) invoices
 * @property {string|null} client_id null for general (internal) invoices
 * @property {boolean} is_general true when project_id/client_id are null
 * @property {string|null} issue_date
 * @property {string|null} due_date
 * @property {number|string} subtotal
 * @property {number|string} tax_total
 * @property {number|string} total
 * @property {string|null} notes
 * @property {InvoiceLineItem[]} line_items
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {object} ProjectOverviewResponse
 * @property {string} project_id
 * @property {string} name
 * @property {string} status
 * @property {number} milestone_total
 * @property {number} milestone_completed
 * @property {number} milestone_completion_pct
 * @property {string} total_invoiced decimal-as-string
 * @property {string} total_paid decimal-as-string
 * @property {string} balance_due decimal-as-string
 * @property {Array<{ id: string, number: string|null, status: string, total: string }>} linked_invoices
 * @property {Array<{ service_id: string, service_name: string, total_invoiced: string, total_paid: string, total_outstanding: string }>} service_breakdown
 */

/**
 * @typedef {object} TransactionAllocation
 * @property {string} id
 * @property {string} line_item_id
 * @property {string} amount decimal-as-string
 */

/**
 * @typedef {object} Transaction
 * @property {string} id
 * @property {string} invoice_id
 * @property {string} amount decimal-as-string
 * @property {'debit'|'credit'} direction debit = payment (money in), credit = refund (money out)
 * @property {'bank_transfer'|'card'|'cash'|'other'} method
 * @property {string} reference_note
 * @property {string|null} recorded_by_id
 * @property {string} recorded_at ISO datetime
 * @property {TransactionAllocation[]} allocations
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, status?: string, project_id?: string, client_id?: string }} [params]
 *   `client_id` filters to that client's project invoices (general/internal excluded server-side).
 * @returns {Promise<{ items: InvoiceListItem[], total: number, page: number, page_size: number }>}
 */
export function listInvoices(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/tenant/invoices', { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<InvoiceDetailResponse>}
 */
export function getInvoice(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(id)}`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{
 *   project_id?: string,
 *   issue_date?: string,
 *   due_date?: string,
 *   notes?: string,
 *   line_items: Array<{ project_service_id?: string, description?: string, unit_price?: string|number, quantity?: number, entry_date?: string }>
 * }} body Create payload; omit project_id for general (internal) invoices
 * @returns {Promise<InvoiceDetailResponse>}
 */
export function createInvoice(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/invoices', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {Record<string, any>} body partial fields (issue_date, due_date, notes, line_items)
 * @returns {Promise<InvoiceDetailResponse>}
 */
export function updateInvoice(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(id)}`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<null>} 204 on success
 */
export function deleteInvoice(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(id)}`, {
		method: 'DELETE',
		token
	});
}

/**
 * Record a payment against an invoice. `allocations` null/omitted means the
 * backend auto-allocates proportionally; pass it to override manually.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @param {{
 *   amount: string,
 *   method: 'bank_transfer'|'card'|'cash'|'other',
 *   reference_note?: string,
 *   recorded_at?: string,
 *   allocations?: Array<{ line_item_id: string, amount: string }>
 * }} payload
 * @returns {Promise<Transaction>}
 */
export function recordTransaction(fetchFn, token, invoiceId, payload) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(invoiceId)}/transactions`, {
		method: 'POST',
		token,
		body: payload
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @returns {Promise<Transaction[]>}
 */
export function listTransactions(fetchFn, token, invoiceId) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(invoiceId)}/transactions`, {
		token
	});
}

/**
 * Record a refund (credit transaction) against an invoice. Cannot exceed the
 * invoice's net paid amount (server-enforced).
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @param {{
 *   amount: string,
 *   method?: 'bank_transfer'|'card'|'cash'|'other',
 *   reference_note?: string
 * }} payload
 * @returns {Promise<Transaction>}
 */
export function refundInvoice(fetchFn, token, invoiceId, payload) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(invoiceId)}/refund`, {
		method: 'POST',
		token,
		body: payload
	});
}

/**
 * Apply client advance balance to an issued/partially-paid invoice. Omitting
 * `amount` applies as much as the advance balance + invoice balance allow.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @param {string} [amount] decimal-as-string, optional
 * @returns {Promise<{ applied: string, advance_balance: string }>}
 */
export function applyAdvance(fetchFn, token, invoiceId, amount) {
	/** @type {Record<string, any>} */
	const body = {};
	if (amount != null && amount !== '') body.amount = amount;
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(invoiceId)}/apply-advance`, {
		method: 'POST',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<InvoiceDetailResponse>}
 */
export function issueInvoice(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(id)}/issue`, {
		method: 'POST',
		token
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<InvoiceDetailResponse>}
 */
export function voidInvoice(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/invoices/${encodeURIComponent(id)}/void`, {
		method: 'POST',
		token
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @returns {Promise<ProjectOverviewResponse>}
 */
export function getProjectOverview(fetchFn, token, projectId) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(projectId)}/overview`, { token });
}

/**
 * Fetch a raw binary payload with a Bearer token.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} path API path starting with '/', relative to /api/v1
 * @param {string} token
 * @returns {Promise<Blob>}
 * @throws {ApiError}
 */
async function fetchBlob(fetchFn, path, token) {
	const res = await fetchFn(`${BASE_URL}${path}`, {
		headers: { Authorization: `Bearer ${token}` }
	});
	if (!res.ok) {
		let data = null;
		try {
			data = await res.json();
		} catch {
			// non-JSON error body; fall through to generic error
		}
		const envelope = data && data.error ? data.error : {};
		throw new ApiError(
			res.status,
			envelope.code ?? 'UNKNOWN',
			envelope.message ?? res.statusText,
			envelope.details ?? {}
		);
	}
	return res.blob();
}

/**
 * Download an invoice PDF attachment. Must run in the browser (uses
 * `document`); call from an event handler, not a load function.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @param {string} filename e.g. "INV-0001.pdf"
 * @returns {Promise<void>}
 * @throws {ApiError}
 */
export async function downloadInvoicePdf(fetchFn, token, invoiceId, filename) {
	const blob = await fetchBlob(
		fetchFn,
		`/tenant/invoices/${encodeURIComponent(invoiceId)}/pdf`,
		token
	);
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}

/**
 * Open an invoice PDF in a new tab. The PDF endpoint requires an Authorization
 * header, so the blob is fetched first and opened via an object URL (revoked
 * after 60s so the new tab keeps the loaded document).
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @param {string} filename e.g. "INV-0001.pdf"
 * @returns {Promise<void>}
 * @throws {ApiError}
 */
// eslint-disable-next-line no-unused-vars -- filename kept for parity with the download helper
export async function viewInvoicePdf(fetchFn, token, invoiceId, filename) {
	const blob = await fetchBlob(
		fetchFn,
		`/tenant/invoices/${encodeURIComponent(invoiceId)}/pdf`,
		token
	);
	const url = URL.createObjectURL(blob);
	window.open(url, '_blank');
	setTimeout(() => URL.revokeObjectURL(url), 60000);
}
