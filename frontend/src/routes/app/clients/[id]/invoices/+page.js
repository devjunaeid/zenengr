import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

/**
 * Invoices tab: the given client's invoices (general/internal invoices are
 * excluded server-side when filtering by client_id), paginated + status
 * filter. The client record comes from the parent layout ([id]/+layout.js).
 *
 * Also fetches the client's projects so the "New invoice" CTA can preselect
 * the client's first active project (mirrors the project_id deep link the
 * invoice-new page already supports).
 *
 * @param {{ fetch: typeof fetch, params: { id: string }, url: URL }} event
 */
export async function load({ fetch, params, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	const status = url.searchParams.get('status') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const [invoices, projects] = await Promise.all([
		invoiceApi.listInvoices(fetch, token, {
			page,
			page_size: 20,
			client_id: params.id,
			...(status && { status })
		}),
		// Failures degrade to an empty list so the tab still renders.
		projectApi
			.listProjects(fetch, token, { page_size: 100, client_id: params.id })
			.catch(() => ({ items: [] }))
	]);

	const firstActiveProject = projects.items.find((p) => p.status === 'active');

	return {
		invoices,
		filters: { status, page },
		newInvoiceProjectId: firstActiveProject?.id ?? ''
	};
}
