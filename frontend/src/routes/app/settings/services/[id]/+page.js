import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as serviceApi from '$lib/api/services.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, params: { id: string } }} event */
export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);
	try {
		const service = await serviceApi.getService(fetch, token, params.id);
		return { service };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Service not found');
		}
		throw e;
	}
}
