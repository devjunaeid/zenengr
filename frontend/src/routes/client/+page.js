import * as portalApi from '$lib/api/portal.js';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await portalAuth.init(fetch);
	const token = /** @type {string} */ (portalAuth.token);

	const [projects, invoices] = await Promise.all([
		portalApi.listClientProjects(fetch, token, { page: 1, page_size: 5 }).catch(() => ({ items: [], total: 0 })),
		portalApi.listClientInvoices(fetch, token, { page: 1, page_size: 5 }).catch(() => ({ items: [], total: 0 }))
	]);

	return { projects, invoices };
}
