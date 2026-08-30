import { apiFetch } from './client.js';

/**
 * Tenant role-management endpoints (staff realm, /api/v1).
 */

/**
 * @typedef {object} RolePermission
 * @property {string} action
 * @property {string} resource
 * @property {boolean} granted
 */

/**
 * @typedef {object} TenantRole
 * @property {string} id
 * @property {string} name
 * @property {string|null} description
 * @property {boolean} is_system
 * @property {string|null} tenant_id
 * @property {RolePermission[]} permissions
 */

/**
 * @typedef {object} PermissionCatalogEntry
 * @property {string} action
 * @property {string} resource
 * @property {string} label
 * @property {string} group
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<TenantRole[]>}
 */
export function getRoles(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/roles', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<PermissionCatalogEntry[]>}
 */
export function getPermissionCatalog(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/roles/permissions', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<PermissionCatalogEntry[]>}
 */
export function getProjectPermissionCatalog(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/roles/project-permissions', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ name: string, description?: string|null, permissions: RolePermission[] }} body
 * @returns {Promise<TenantRole>}
 */
export function createRole(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/roles', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} roleId
 * @param {{ name?: string, description?: string|null, permissions?: RolePermission[] }} body
 * @returns {Promise<TenantRole>}
 */
export function updateRole(fetchFn, token, roleId, body) {
	return apiFetch(fetchFn, `/tenant/roles/${roleId}`, { method: 'PATCH', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} roleId
 * @returns {Promise<null>}
 */
export function deleteRole(fetchFn, token, roleId) {
	return apiFetch(fetchFn, `/tenant/roles/${roleId}`, { method: 'DELETE', token });
}

/**
 * Reset a system role (manager/employee) to its default permissions.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} roleId
 * @returns {Promise<TenantRole>}
 */
export function resetRole(fetchFn, token, roleId) {
	return apiFetch(fetchFn, `/tenant/roles/${roleId}/reset`, { method: 'POST', token });
}
