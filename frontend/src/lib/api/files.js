import { ApiError, apiFetch, BASE_URL } from './client.js';

/**
 * Tenant file storage API endpoints (FEAT-012).
 *
 * Three visibility scopes mirror the server: USER ("My files", creator
 * only), TENANT ("Team files", all staff), PROJECT ("Project files",
 * staff with project access + the project's client). Read endpoints are
 * open to all staff; writes are server-enforced (owner for USER scope,
 * admin/manager for TENANT/PROJECT) and the UI mirrors this.
 */

/**
 * @typedef {object} FolderTreeNode
 * @property {string|null} id null for the virtual "My files" root
 * @property {string} name
 * @property {'user'|'tenant'|'project'} scope
 * @property {string|null} project_id set on project-scope nodes
 * @property {FolderTreeNode[]} children
 */

/**
 * @typedef {object} FolderItem
 * @property {string} id
 * @property {string} name
 * @property {'user'|'tenant'|'project'} scope
 * @property {string|null} parent_id
 * @property {string|null} project_id
 * @property {string} created_at
 */

/**
 * @typedef {object} FileAssetItem
 * @property {string} id
 * @property {string} name
 * @property {'user'|'tenant'|'project'} scope
 * @property {string|null} folder_id
 * @property {string|null} project_id
 * @property {string} content_type
 * @property {number} size_bytes
 * @property {string} sha256
 * @property {string} created_by_id
 * @property {'user'|'client_user'} created_by_type
 * @property {string} created_at
 */

/**
 * @typedef {object} FileListResponse
 * @property {FileAssetItem[]} items
 * @property {number} total
 * @property {number} page
 * @property {number} page_size
 */

/**
 * Fetch the folder tree. Roots: virtual "My files" (id null), "Team files",
 * "Project files" (children are per-project folders).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @returns {Promise<FolderTreeNode[]>}
 */
export function listFolders(fetchFn, token) {
	return apiFetch(fetchFn, '/tenant/files/folders', { token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ name: string, scope: 'user'|'tenant'|'project', parent_id?: string|null, project_id?: string|null }} body
 * @returns {Promise<FolderItem>}
 */
export function createFolder(fetchFn, token, body) {
	return apiFetch(fetchFn, '/tenant/files/folders', { method: 'POST', token, body });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ name: string }} body
 * @returns {Promise<FolderItem>}
 */
export function renameFolder(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/files/folders/${encodeURIComponent(id)}`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<null>} 204 on success (409 if the folder is not empty)
 */
export function deleteFolder(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/files/folders/${encodeURIComponent(id)}`, {
		method: 'DELETE',
		token
	});
}

/**
 * Upload a file as multipart FormData (file, scope, folder_id?, project_id?).
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {FormData} formData
 * @returns {Promise<FileAssetItem>}
 * @throws {ApiError}
 */
export async function uploadFile(fetchFn, token, formData) {
	const res = await fetchFn(`${BASE_URL}/tenant/files/upload`, {
		method: 'POST',
		headers: { Authorization: `Bearer ${token}` },
		body: formData
	});
	const data = await res.json().catch(() => null);
	if (!res.ok) {
		const envelope = data && data.error ? data.error : {};
		throw new ApiError(
			res.status,
			envelope.code ?? 'UNKNOWN',
			envelope.message ?? res.statusText,
			envelope.details ?? {}
		);
	}
	return data;
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {{ folder_id?: string, scope?: string, project_id?: string, page?: number, page_size?: number, q?: string }} [params]
 * @returns {Promise<FileListResponse>}
 */
export function listFiles(fetchFn, token, params = {}) {
	return apiFetch(fetchFn, '/tenant/files', { token, params });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<FileAssetItem>}
 */
export function getFile(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/files/${encodeURIComponent(id)}`, { token });
}

/**
 * Download a file's content as an attachment. Must run in the browser
 * (uses `document`); call from an event handler, not a load function.
 *
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {string} filename
 * @returns {Promise<void>}
 * @throws {ApiError}
 */
export async function downloadFile(fetchFn, token, id, filename) {
	const res = await fetchFn(`${BASE_URL}/tenant/files/${encodeURIComponent(id)}/content`, {
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
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @returns {Promise<null>} 204 on success
 */
export function deleteFile(fetchFn, token, id) {
	return apiFetch(fetchFn, `/tenant/files/${encodeURIComponent(id)}`, { method: 'DELETE', token });
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ name: string }} body
 * @returns {Promise<FileAssetItem>}
 */
export function renameFile(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/files/${encodeURIComponent(id)}`, {
		method: 'PATCH',
		token,
		body
	});
}

/**
 * @param {typeof fetch} fetchFn
 * @param {string} token
 * @param {string} id
 * @param {{ folder_id: string|null }} body
 * @returns {Promise<FileAssetItem>}
 */
export function moveFile(fetchFn, token, id, body) {
	return apiFetch(fetchFn, `/tenant/files/${encodeURIComponent(id)}/move`, {
		method: 'POST',
		token,
		body
	});
}
