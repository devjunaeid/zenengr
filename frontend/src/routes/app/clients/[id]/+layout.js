import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as clientApi from '$lib/api/clients.js';
import { auth } from '$lib/stores/auth.svelte.js';

/**
 * Loads the client once for all tabs (Overview / Projects / Invoices) under
 * /app/clients/[id]. Child pages receive it via the merged `data` prop.
 *
 * @param {{ fetch: typeof fetch, params: { id: string } }} event
 */
export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	try {
		const client = await clientApi.getClient(fetch, token, params.id);
		return { client };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Client not found');
		}
		throw e;
	}
}
