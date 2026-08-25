import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, params, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const status = url.searchParams.get('status') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const [invoices, projects] = await Promise.all([
		invoiceApi.listInvoices(fetch, token, {
			page,
			page_size: 20,
			client_id: params.id,
			...(status && { status })
		}),
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
