import * as portalApi from '$lib/api/portal.js';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	await portalAuth.init(fetch);
	const token = /** @type {string} */ (portalAuth.token);

	const status = url.searchParams.get('status') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const invoices = await portalApi.listClientInvoices(fetch, token, {
		page,
		page_size: 20,
		...(status && { status })
	});

	return { invoices, filters: { status, page } };
}
