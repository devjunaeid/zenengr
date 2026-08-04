import { env } from '$env/dynamic/public';

export const BASE_URL = (env.PUBLIC_API_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');

/**
 * Error thrown for any non-2xx backend response, parsed from the
 * backend error envelope `{ "error": { code, message, details } }`.
 */
export class ApiError extends Error {
	/**
	 * @param {number} status HTTP status code
	 * @param {string} code machine-readable error code from the backend
	 * @param {string} message human-readable message
	 * @param {Record<string, any>} [details] field-level details
	 */
	constructor(status, code, message, details = {}) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.code = code;
		this.details = details;
	}
}

/**
 * @typedef {object} RequestOptions
 * @property {string} [method]
 * @property {string|null} [token] Bearer token
 * @property {any} [body] JSON body (ignored for GET)
 * @property {Record<string, any>} [params] query string params (null/undefined/'' skipped)
 */

/**
 * Thin fetch wrapper around the FastAPI backend. Always pass SvelteKit's
 * `event.fetch` from load functions so requests work uniformly.
 *
 * @param {typeof fetch} fetchFn fetch implementation (event.fetch in load, window.fetch in handlers)
 * @param {string} path API path starting with '/', relative to /api/v1
 * @param {RequestOptions} [options]
 * @returns {Promise<any>} parsed JSON body (null for 204)
 * @throws {ApiError}
 */
export async function apiFetch(fetchFn, path, options = {}) {
	const { method = 'GET', token = null, body = undefined, params = {} } = options;

	const url = new URL(`${BASE_URL}${path}`);
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null && value !== '') {
			url.searchParams.set(key, String(value));
		}
	}

	/** @type {Record<string, string>} */
	const headers = {};
	if (body !== undefined) headers['Content-Type'] = 'application/json';
	if (token) headers.Authorization = `Bearer ${token}`;

	const res = await fetchFn(url.toString(), {
		method,
		headers,
		body: body === undefined ? undefined : JSON.stringify(body)
	});

	if (res.status === 204) return null;

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
