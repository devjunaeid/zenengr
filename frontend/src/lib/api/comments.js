import { apiFetch } from './client.js';

/**
 * Project comment API (TODO-101). One comment thread per project, shared
 * between the tenant (staff) realm and the client portal realm.
 *
 * - Tenant realm: staff see all comments including internal ones and can
 *   post internal-only comments (`is_internal: true`).
 * - Client realm: shared comments only; internal comments are never
 *   returned and the client payload has no `is_internal` flag.
 */

/**
 * @typedef {object} CommentResponse
 * @property {string} id
 * @property {string} project_id
 * @property {string|null} author_id
 * @property {'tenant_admin'|'tenant_manager'|'tenant_employee'|'client_user'} author_type
 * @property {string} author_name
 * @property {string} content
 * @property {boolean} is_internal
 * @property {string} created_at ISO datetime
 */

/**
 * Realm the request is made against. 'admin' maps to the tenant realm.
 * @typedef {'admin'|'client'} CommentRealm
 */

/**
 * List comments for a project, ordered by created_at ascending.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {{ realm?: CommentRealm }} [options]
 * @returns {Promise<CommentResponse[]>}
 */
export function listComments(fetchFn, token, projectId, options = {}) {
	const { realm = 'admin' } = options;
	const base = realm === 'client' ? 'client' : 'tenant';
	return apiFetch(fetchFn, `/${base}/projects/${encodeURIComponent(projectId)}/comments`, {
		token
	});
}

/**
 * Post a comment to a project's thread.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {{ content: string, is_internal?: boolean }} body
 * @param {{ realm?: CommentRealm }} [options]
 * @returns {Promise<CommentResponse>}
 */
export function postComment(fetchFn, token, projectId, body, options = {}) {
	const { realm = 'admin' } = options;
	const base = realm === 'client' ? 'client' : 'tenant';
	// Client realm payload is `{ content }` only; is_internal is a staff flag.
	const payload =
		realm === 'client'
			? { content: body.content }
			: { content: body.content, is_internal: body.is_internal ?? false };
	return apiFetch(fetchFn, `/${base}/projects/${encodeURIComponent(projectId)}/comments`, {
		method: 'POST',
		token,
		body: payload
	});
}

/**
 * Edit a comment's content (tenant realm only; requires edit/comments).
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {string} commentId
 * @param {string} content
 * @returns {Promise<CommentResponse>}
 */
export function editComment(fetchFn, token, projectId, commentId, content) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/comments/${encodeURIComponent(commentId)}`,
		{
			method: 'PATCH',
			token,
			body: { content }
		}
	);
}

/**
 * Delete a comment (tenant realm only; requires edit/comments). Resolves to
 * null on success (HTTP 204).
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} projectId
 * @param {string} commentId
 * @returns {Promise<null>}
 */
export function deleteComment(fetchFn, token, projectId, commentId) {
	return apiFetch(
		fetchFn,
		`/tenant/projects/${encodeURIComponent(projectId)}/comments/${encodeURIComponent(commentId)}`,
		{
			method: 'DELETE',
			token
		}
	);
}
