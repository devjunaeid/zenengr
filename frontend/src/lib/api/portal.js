import { ApiError, apiFetch, BASE_URL } from './client.js';

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
 * @typedef {object} ClientProjectListItem
 * @property {string} id
 * @property {string} name
 * @property {string} status
 * @property {string|null} start_date ISO date
 * @property {number} milestone_total
 * @property {number} milestone_completed
 * @property {number} milestone_completion_pct
 * @property {string} created_at
 */

/**
 * @typedef {object} ClientProjectServiceItem
 * @property {string} id
 * @property {string} service_name
 * @property {'active'|'cancelled'} status
 * @property {string|null} price_at_attachment decimal-as-string
 */

/**
 * @typedef {object} ClientProjectMilestoneItem
 * @property {string} id
 * @property {string} name
 * @property {number} sequence_order
 * @property {'pending'|'in_progress'|'completed'|'blocked'} status
 * @property {string|null} planned_date
 * @property {string|null} actual_date
 * @property {string|null} assignee_id
 */

/**
 * @typedef {object} ClientProjectDetailResponse
 * @property {string} id
 * @property {string} name
 * @property {string} status
 * @property {string|null} start_date
 * @property {string} client_id
 * @property {number} milestone_total
 * @property {number} milestone_completed
 * @property {number} milestone_completion_pct
 * @property {ClientProjectServiceItem[]} services
 * @property {ClientProjectMilestoneItem[]} milestones
 * @property {{ total_invoiced?: string, total_paid?: string, balance_due?: string }|null} financials
 * @property {Array<{ id: string, number: string|null, status: string, total: string }>} linked_invoices
 */

/**
 * @typedef {object} ClientInvoiceListItem
 * @property {string} id
 * @property {string|null} invoice_number null while draft
 * @property {'draft'|'issued'|'partially_paid'|'paid'} status (void excluded)
 * @property {string} project_id
 * @property {string} project_name
 * @property {string|null} issue_date ISO date
 * @property {string|null} due_date ISO date
 * @property {string} total decimal-as-string
 * @property {string} created_at
 */

/**
 * @typedef {object} ClientInvoiceLineItem
 * @property {string} id
 * @property {string} description
 * @property {number|string} quantity decimal-as-string or number
 * @property {number|string} unit_price decimal-as-string or number
 * @property {number|string} amount decimal-as-string or number
 * @property {string|null} service_id
 * @property {string|null} project_service_id null for custom lines
 */

/**
 * @typedef {object} ClientInvoiceDetailResponse
 * @property {string} id
 * @property {string|null} invoice_number null while draft
 * @property {'draft'|'issued'|'partially_paid'|'paid'|'void'} status
 * @property {string} project_id
 * @property {string} project_name
 * @property {string|null} issue_date
 * @property {string|null} due_date
 * @property {string} subtotal decimal-as-string
 * @property {string} tax_total decimal-as-string
 * @property {string} total decimal-as-string
 * @property {string|null} notes
 * @property {string} paid_amount decimal-as-string
 * @property {string} balance_due decimal-as-string
 * @property {ClientInvoiceLineItem[]} line_items
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {object} ClientTransactionAllocation
 * @property {string} id
 * @property {string} line_item_id
 * @property {string} amount decimal-as-string
 */

/**
 * @typedef {object} ClientTransaction
 * @property {string} id
 * @property {string} invoice_id
 * @property {string} amount decimal-as-string
 * @property {'bank_transfer'|'card'|'cash'|'other'} method
 * @property {string} reference_note
 * @property {string|null} recorded_by_id
 * @property {string} recorded_at ISO datetime
 * @property {ClientTransactionAllocation[]} allocations
 */

/**
 * @typedef {{ page?: number, page_size?: number, status?: string }} ClientListParams
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

// ── Client portal data (client realm) ────────────────────────────────────────

/**
 * List the client's own projects with milestone completion rollups.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {ClientListParams} [params]
 * @returns {Promise<{ items: ClientProjectListItem[], total: number, page: number, page_size: number }>}
 */
export function listClientProjects(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/client/projects', { token, params });
}

/**
 * Project detail scoped to the client: services, milestones, financials.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<ClientProjectDetailResponse>}
 */
export function getClientProject(fetchFn, token, id) {
	return apiFetch(fetchFn, `/client/projects/${encodeURIComponent(id)}`, { token });
}

/**
 * List the client's invoices (void invoices excluded).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {ClientListParams} [params]
 * @returns {Promise<{ items: ClientInvoiceListItem[], total: number, page: number, page_size: number }>}
 */
export function listClientInvoices(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/client/invoices', { token, params });
}

/**
 * Invoice detail with line items + paid/balance amounts (client-scoped).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<ClientInvoiceDetailResponse>}
 */
export function getClientInvoice(fetchFn, token, id) {
	return apiFetch(fetchFn, `/client/invoices/${encodeURIComponent(id)}`, { token });
}

/**
 * Payments recorded against one of the client's invoices.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @returns {Promise<ClientTransaction[]>}
 */
export function listClientTransactions(fetchFn, token, invoiceId) {
	return apiFetch(fetchFn, `/client/invoices/${encodeURIComponent(invoiceId)}/transactions`, {
		token
	});
}

/**
 * @typedef {object} ClientFileAssetItem
 * @property {string} id
 * @property {string} name
 * @property {'user'|'tenant'|'project'} scope
 * @property {string|null} folder_id
 * @property {string|null} project_id
 * @property {string} content_type
 * @property {number} size_bytes
 * @property {string} sha256
 * @property {string} created_at
 */

/**
 * Files shared with the client for one of their projects (read-only).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {{ page?: number, page_size?: number }} [params]
 * @returns {Promise<{ items: ClientFileAssetItem[], total: number, page: number, page_size: number }>}
 */
export function listClientProjectFiles(fetchFn, token, projectId, params = {}) {
	return apiFetch(fetchFn, `/client/projects/${encodeURIComponent(projectId)}/files`, {
		token,
		params
	});
}

/**
 * Download a file shared with the client. Must run in the browser (uses
 * `document`); call from an event handler, not a load function.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} fileId
 * @param {string} filename
 * @returns {Promise<void>}
 * @throws {ApiError}
 */
export async function downloadClientFile(fetchFn, token, fileId, filename) {
	const res = await fetchFn(`${BASE_URL}/client/files/${encodeURIComponent(fileId)}/content`, {
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
	const blob = await res.blob();
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
 * Download one of the client's invoices as a PDF attachment. Must run in the
 * browser (uses `document`); call from an event handler, not a load function.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} invoiceId
 * @param {string} filename e.g. "INV-0001.pdf"
 * @returns {Promise<void>}
 * @throws {ApiError}
 */
export async function downloadClientInvoicePdf(fetchFn, token, invoiceId, filename) {
	const res = await fetchFn(`${BASE_URL}/client/invoices/${encodeURIComponent(invoiceId)}/pdf`, {
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
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}
