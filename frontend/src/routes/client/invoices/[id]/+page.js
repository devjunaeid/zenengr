import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as portalApi from '$lib/api/portal.js';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

/** @param {{ fetch: typeof fetch, params: { id: string } }} event */
export async function load({ fetch, params }) {
	await portalAuth.init(fetch);
	const token = /** @type {string} */ (portalAuth.token);

	try {
		const [invoice, transactions] = await Promise.all([
			portalApi.getClientInvoice(fetch, token, params.id),
			portalApi.listClientTransactions(fetch, token, params.id).catch(() => [])
		]);
		return { invoice, transactions };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Invoice not found');
		}
		throw e;
	}
}
