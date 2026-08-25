import { apiFetch } from './client.js';

/**
 * Tenant project-management API endpoints (FEAT-007).
 *
 * GET endpoints are accessible to all staff (admin, manager, employee).
 * Write endpoints (create/update/attach/updateMilestone) require admin or
 * manager; the server enforces and the UI mirrors this.
 */

/**
 * @typedef {object} ProjectServiceItem
 * @property {string} id project_service id (link row)
 * @property {string} service_id
 * @property {string} service_name
 * @property {'active'|'cancelled'} status
 * @property {string|null} price_at_attachment decimal-as-string
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {object} ProjectMilestoneItem
 * @property {string} id
 * @property {string} project_service_id
 * @property {string} service_id
 * @property {string} name
 * @property {number} sequence_order
 * @property {'pending'|'in_progress'|'completed'|'blocked'} status
 * @property {string|null} planned_date ISO date
 * @property {string|null} actual_date ISO date
 * @property {string|null} assignee_id
 * @property {string|null} description
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {object} ProjectListItem
 * @property {string} id
 * @property {string} name
 * @property {string} client_id
 * @property {'draft'|'active'|'on_hold'|'completed'|'cancelled'} status
 * @property {string|null} start_date
 * @property {string|null} owner_id
 * @property {number} service_count
 * @property {number} milestone_total
 * @property {number} milestone_completed
 * @property {boolean} auto_invoice
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {object} ProjectDetailResponse
 * @property {string} id
 * @property {string} name
 * @property {string} client_id
 * @property {'draft'|'active'|'on_hold'|'completed'|'cancelled'} status
 * @property {string|null} start_date
 * @property {string|null} owner_id
 * @property {boolean} auto_invoice
 * @property {string} created_at
 * @property {string} updated_at
 * @property {ProjectServiceItem[]} services
 * @property {ProjectMilestoneItem[]} milestones
 */

/**
 * @typedef {object} ProjectCreateResponse
 * @property {string} id
 * @property {string} name
 * @property {string} client_id
 * @property {'draft'|'active'|'on_hold'|'completed'|'cancelled'} status
 * @property {string|null} start_date
 * @property {string|null} owner_id
 * @property {boolean} auto_invoice
 * @property {number} service_count
 * @property {number} milestone_count
 * @property {string} created_at
 */

/**
 * @typedef {object} AttachServiceResponse
 * @property {string} project_service_id
 * @property {string} service_id
 * @property {string} service_name
 * @property {number} milestone_count
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, status?: string, client_id?: string, sort?: string, q?: string }} [params]
 * @returns {Promise<{ items: ProjectListItem[], total: number, page: number, page_size: number }>}
 */
export function listProjects(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/tenant/projects', { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<ProjectDetailResponse>}
 */
export function getProject(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(id)}`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ name: string, client_id: string, service_ids: string[], service_prices?: Record<string, number|string>, start_date?: string|null, owner_id?: string|null, auto_invoice?: boolean }} body
 * @returns {Promise<ProjectCreateResponse>}
 */
export function createProject(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/projects', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {Record<string, any>} body partial fields (name, status, start_date, owner_id, auto_invoice)
 * @returns {Promise<ProjectDetailResponse>}
 */
export function updateProject(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(id)}`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {{ service_id: string, price?: number|string }} body price overrides the service default (price_at_attachment); omit to use the default
 * @returns {Promise<AttachServiceResponse>}
 */
export function attachService(fetchFn, token, projectId, body) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(projectId)}/services`, {
		method: 'POST',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {string} milestoneId
 * @param {Record<string, any>} body partial fields (status, planned_date, actual_date, assignee_id)
 * @returns {Promise<ProjectMilestoneItem>}
 */
export function updateMilestone(fetchFn, token, projectId, milestoneId, body) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/milestones/${encodeURIComponent(milestoneId)}`,
		{ method: 'PATCH', token, body }
	);
}

/**
 * @typedef {object} LedgerEntry
 * @property {string} id
 * @property {'charge'|'payment'|'refund'} type
 * @property {string} amount signed decimal-as-string (charges may be negative for reversals, payments positive, refunds negative)
 * @property {string} description
 * @property {'project_service'|'transaction'|'manual_adjustment'} source_type
 * @property {string|null} source_id
 * @property {string|null} invoice_ref set when a charge is covered by an issued invoice
 * @property {string|null} invoice_number null while the covering invoice is a draft
 * @property {string|null} entry_date ISO date
 * @property {string} created_at ISO datetime
 */

/**
 * @typedef {object} LedgerSummary
 * @property {string} subtotal decimal-as-string
 * @property {'percentage'|'fixed'|null} discount_type
 * @property {string|null} discount_value null when no discount
 * @property {string} discount_amount decimal-as-string
 * @property {string} total decimal-as-string
 * @property {string} paid decimal-as-string
 * @property {string} due decimal-as-string
 */

/**
 * @typedef {object} LedgerResponse
 * @property {LedgerEntry[]} entries chronological, oldest first
 * @property {LedgerSummary} summary
 */

/**
 * Project ledger: append-only charges + derived payment/refund stream with a
 * live balance summary (FEAT-018).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<LedgerResponse>}
 */
export function getProjectLedger(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(id)}/ledger`, { token });
}

/**
 * Replace the project discount (single active; old value replaced, not stacked).
 * `discount_type: null` clears the discount.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ discount_type: 'percentage'|'fixed'|null, discount_value: number|null }} body
 * @returns {Promise<{ discount_type: 'percentage'|'fixed'|null, discount_value: string|null }>}
 */
export function setProjectDiscount(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(id)}/discount`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * Manual ledger adjustment (admin/manager only). Signed amount: positive adds
 * to the total, negative offsets it.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ amount: string, description: string }} body
 * @returns {Promise<LedgerEntry>} 201
 */
export function addLedgerAdjustment(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(id)}/ledger/adjustments`, {
		method: 'POST',
		token,
		body
	});
}

/**
 * Live project statement (FEAT-019).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<LedgerResponse>}
 */
export function getProjectStatement(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(id)}/statement`, { token });
}

/**
 * Generate and issue an official cumulative statement invoice (FEAT-019).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<any>}
 */
export function generateStatementInvoice(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/projects/${encodeURIComponent(id)}/generate-statement-invoice`, {
		method: 'POST',
		token
	});
}

/**
 * Download project statement PDF.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {string} filename
 * @returns {Promise<void>}
 */
export async function downloadProjectStatementPdf(fetchFn, token, projectId, filename) {
	const res = await fetchFn(`/api/v1/tenant/projects/${encodeURIComponent(projectId)}/statement/pdf`, {
		headers: { Authorization: `Bearer ${token}` }
	});
	if (!res.ok) {
		throw new ApiError(res.status, 'UNKNOWN', 'Could not download statement PDF', {});
	}
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}

/**
 * Open project statement PDF in a new tab.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @returns {Promise<void>}
 */
export async function viewProjectStatementPdf(fetchFn, token, projectId) {
	const res = await fetchFn(`/api/v1/tenant/projects/${encodeURIComponent(projectId)}/statement/pdf`, {
		headers: { Authorization: `Bearer ${token}` }
	});
	if (!res.ok) {
		throw new ApiError(res.status, 'UNKNOWN', 'Could not open statement PDF', {});
	}
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	window.open(url, '_blank', 'noopener,noreferrer');
}
