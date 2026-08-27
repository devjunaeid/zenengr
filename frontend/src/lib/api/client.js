import { PUBLIC_API_URL } from '$env/static/public';

export const BASE_URL = (PUBLIC_API_URL || 'https://api-zenengr.synafeia.com/api/v1').replace(/\/$/, '');

/**
 * Resolve a backend-relative asset URL (e.g. /uploads/logo.png) to an absolute URL on the API origin.
 * @param {string|null|undefined} path
 * @returns {string}
 */
export function assetUrl(path) {
	if (!path) return '';
	if (/^https?:\/\//.test(path)) return path;
	return `${BASE_URL.replace(/\/api\/v1\/?$/, '')}${path.startsWith('/') ? path : `/${path}`}`;
}

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
 * @property {AbortSignal} [signal] optional caller-owned abort signal, forwarded to fetch
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
	const {
		method = 'GET',
		token = null,
		body = undefined,
		params = {},
		signal = undefined
	} = options;

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

	// 15s ceiling on every request so API loads can never hang forever.
	// Caller-supplied aborts are forwarded as-is; only the timeout becomes an ApiError.
	const controller = new AbortController();
	let timedOut = false;
	const timeoutId = setTimeout(() => {
		timedOut = true;
		controller.abort();
	}, 15000);
	const onCallerAbort = () => controller.abort();
	if (signal) {
		if (signal.aborted) {
			controller.abort();
		} else {
			signal.addEventListener('abort', onCallerAbort, { once: true });
		}
	}

	let res;
	try {
		res = await fetchFn(url.toString(), {
			method,
			headers,
			body: body === undefined ? undefined : JSON.stringify(body),
			signal: controller.signal
		});
	} catch (err) {
		if (timedOut) {
			throw new ApiError(0, 'TIMEOUT', 'Request timed out');
		}
		throw err;
	} finally {
		clearTimeout(timeoutId);
		if (signal) signal.removeEventListener('abort', onCallerAbort);
	}

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
