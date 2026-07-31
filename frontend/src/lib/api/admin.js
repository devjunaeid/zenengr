import { apiFetch } from './client.js';

/**
 * Super Admin API endpoints. All require a super_admin Bearer token.
 */

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<Array<{ id: string, name: string, description: string, max_admin_users: number, max_clients: number, max_active_projects: number, max_storage_mb: number, is_active: boolean, created_at: string, updated_at: string, tenant_count: number }>>}
 */
export function listPlans(fetchFn, token) {
	return apiFetch(fetchFn, '/admin/plans', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ name: string, description?: string, max_admin_users: number, max_clients: number, max_active_projects: number, max_storage_mb: number }} body
 */
export function createPlan(fetchFn, token, body) {
	return apiFetch(fetchFn, '/admin/plans', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} planId
 * @param {Record<string, any>} body partial plan fields
 */
export function updatePlan(fetchFn, token, planId, body) {
	return apiFetch(fetchFn, `/admin/plans/${planId}`, { method: 'PATCH', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ page?: number, page_size?: number, status?: string, q?: string }} [params]
 * @returns {Promise<{ items: Array<{ id: string, business_name: string, slug: string, status: string, plan_name: string, created_at: string, active_user_count: number }>, total: number, page: number, page_size: number }>}
 */
export function listTenants(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/admin/tenants', { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} slug
 * @returns {Promise<{ slug: string, available: boolean, valid: boolean }>}
 */
export function slugAvailable(fetchFn, token, slug) {
	return apiFetch(fetchFn, '/admin/tenants/slug-available', { token, params: { slug } });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ business_name: string, slug: string, plan_id: string, admin_email: string, admin_full_name: string }} body
 * @returns {Promise<{ id: string, business_name: string, slug: string, status: string, plan_id: string, admin_email: string, temp_password: string }>}
 */
export function createTenant(fetchFn, token, body) {
	return apiFetch(fetchFn, '/admin/tenants', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 */
export function getTenant(fetchFn, token, tenantId) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @param {Record<string, any>} body business_name / contact_info / branding / logo_url
 */
export function updateTenant(fetchFn, token, tenantId, body) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}`, { method: 'PATCH', token, body });
}

/**
 * Lifecycle action: suspend | reactivate | cancel.
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @param {'suspend'|'reactivate'|'cancel'} action
 */
export function tenantLifecycle(fetchFn, token, tenantId, action) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/${action}`, { method: 'POST', token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 */
export function getSubscription(fetchFn, token, tenantId) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/subscription`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @param {{ plan_id?: string, status?: string, billing_cycle?: string, renewal_date?: string|null }} body
 */
export function updateSubscription(fetchFn, token, tenantId, body) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/subscription`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @returns {Promise<{ resolved: Array<{ key: string, enabled: boolean }>, overrides: Array<{ key: string, enabled: boolean }> }>}
 */
export function getFlags(fetchFn, token, tenantId) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/flags`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @param {string} key
 * @param {boolean} enabled
 */
export function putFlag(fetchFn, token, tenantId, key, enabled) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/flags/${encodeURIComponent(key)}`, {
		method: 'PUT',
		token,
		body: { enabled }
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @param {string} key
 */
export function deleteFlag(fetchFn, token, tenantId, key) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/flags/${encodeURIComponent(key)}`, {
		method: 'DELETE',
		token
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @param {{ page?: number, page_size?: number, action?: string, from?: string, to?: string }} [params]
 * @returns {Promise<{ items: Array<{ id: string, action: string, actor_id: string, actor_type: string, entity_type: string, entity_id: string|null, details: Record<string, any>, created_at: string }>, total: number, page: number, page_size: number }>}
 */
export function getAuditLogs(fetchFn, token, tenantId, params = {}) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/audit-logs`, { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @returns {Promise<Array<{ key: string, value: string|null, permission_level: string, editable: boolean }>>}
 */
export function getTenantSettings(fetchFn, token, tenantId) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/settings`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} tenantId
 * @param {string} key
 * @param {string|null} value
 */
export function updateTenantSetting(fetchFn, token, tenantId, key, value) {
	return apiFetch(fetchFn, `/admin/tenants/${tenantId}/settings/${encodeURIComponent(key)}`, {
		method: 'PATCH',
		token,
		body: { value }
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} planId
 * @returns {Promise<Array<{ key: string, enabled: boolean }>>}
 */
export function listPlanFlagDefaults(fetchFn, token, planId) {
	return apiFetch(fetchFn, `/admin/plans/${planId}/flags`, { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} planId
 * @param {string} key
 * @param {boolean} enabled
 */
export function setPlanFlagDefault(fetchFn, token, planId, key, enabled) {
	return apiFetch(fetchFn, `/admin/plans/${planId}/flags/${encodeURIComponent(key)}`, {
		method: 'PUT',
		token,
		body: { enabled }
	});
}
