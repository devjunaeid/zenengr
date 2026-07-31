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
 * @param {{ name: string, client_id: string, service_ids: string[], start_date?: string|null, owner_id?: string|null }} body
 * @returns {Promise<ProjectCreateResponse>}
 */
export function createProject(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/projects', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {Record<string, any>} body partial fields (name, status, start_date, owner_id)
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
 * @param {{ service_id: string }} body
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
