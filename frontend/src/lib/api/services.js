import { apiFetch } from './client.js';

/**
 * Tenant service-catalog API endpoints.
 *
 * GET endpoints are accessible to all staff (admin, manager, employee).
 * Write endpoints require admin or manager; the server enforces and the UI
 * hides/disables write controls for employees.
 */

/**
 * @typedef {object} MilestoneStep
 * @property {string} [id] present on read, absent on create/replace
 * @property {string} name
 * @property {number} sequence_order
 * @property {number|null} expected_duration_days
 * @property {string|null} [description]
 * @property {string} [created_at]
 * @property {string} [updated_at]
 */

/**
 * @typedef {object} ServiceListItem
 * @property {string} id
 * @property {string} name
 * @property {string|null} description
 * @property {string|null} default_price decimal-as-string, e.g. "1500.00"
 * @property {boolean} is_active
 * @property {number} step_count
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {ServiceListItem & { steps: MilestoneStep[], in_use: boolean, project_count: number }} ServiceDetail
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, is_active?: boolean|string, q?: string, sort?: string }} [params]
 * @returns {Promise<{ items: ServiceListItem[], total: number, page: number, page_size: number }>}
 */
export function listServices(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/tenant/services', { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<ServiceDetail>}
 */
export function getService(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/services/${encodeURIComponent(id)}`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{
 *   name: string,
 *   description?: string|null,
 *   default_price?: number|string|null,
 *   is_active?: boolean,
 *   steps?: Array<{ name: string, sequence_order: number, expected_duration_days?: number|null, description?: string|null }>
 * }} body
 * @returns {Promise<ServiceDetail>}
 */
export function createService(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/services', { method: 'POST', token, body });
}

/**
 * PATCH is partial. When `steps` is provided it REPLACES the full set;
 * the server renumbers sequence_order on save.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {Record<string, any>} body partial fields (any may be null to clear)
 * @returns {Promise<ServiceDetail>}
 */
export function updateService(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/services/${encodeURIComponent(id)}`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<null>}
 */
export function deleteService(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/services/${encodeURIComponent(id)}`, {
		method: 'DELETE',
		token
	});
}
