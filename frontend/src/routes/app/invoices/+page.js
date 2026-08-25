import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const status = url.searchParams.get('status') ?? '';
	const projectId = url.searchParams.get('project_id') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const [invoices, projects] = await Promise.all([
		invoiceApi.listInvoices(fetch, token, {
			page,
			page_size: 20,
			...(status && { status }),
			...(projectId && { project_id: projectId })
		}),
		projectApi.listProjects(fetch, token, { page_size: 100 }).catch(() => ({ items: [] }))
	]);

	return { invoices, projects: projects.items, filters: { status, project_id: projectId, page } };
}
