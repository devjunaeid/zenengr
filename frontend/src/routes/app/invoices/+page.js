import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const status = url.searchParams.get('status') ?? '';
	const invoiceType = url.searchParams.get('type') ?? '';
	const projectId = url.searchParams.get('project_id') ?? '';
	const dateFrom = url.searchParams.get('date_from') ?? '';
	const dateTo = url.searchParams.get('date_to') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	let invoices = { items: [], total: 0, page: 1, page_size: 20 };
	let loadError = null;

	try {
		invoices = await invoiceApi.listInvoices(fetch, token, {
			page,
			page_size: 20,
			...(status && { status }),
			...(invoiceType && { invoice_type: invoiceType }),
			...(projectId && { project_id: projectId }),
			...(dateFrom && { date_from: dateFrom }),
			...(dateTo && { date_to: dateTo })
		});
	} catch (err) {
		console.error('Failed to load invoices:', err);
		loadError = 'Unable to load invoices. Please refresh to try again.';
	}

	const projects = await projectApi
		.listProjects(fetch, token, { page_size: 100 })
		.catch(() => ({ items: [] }));

	return {
		invoices,
		projects: projects.items,
		filters: {
			status,
			type: invoiceType,
			project_id: projectId,
			date_from: dateFrom,
			date_to: dateTo,
			page
		},
		loadError
	};
}
