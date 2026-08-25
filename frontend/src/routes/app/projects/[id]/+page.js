import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import * as serviceApi from '$lib/api/services.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = auth.token;

	try {
		const [project, users, overview, ledger, draftInvoices, invoices] = await Promise.all([
			projectApi.getProject(fetch, token, params.id),
			tenantApi
				.listUsers(fetch, token, { page_size: 100, is_active: true })
				.catch(() => ({ items: [] })),
			invoiceApi.getProjectOverview(fetch, token, params.id).catch(() => null),
			projectApi.getProjectLedger(fetch, token, params.id).catch(() => null),
			invoiceApi
				.listInvoices(fetch, token, { project_id: params.id, status: 'draft', page_size: 5 })
				.catch(() => ({ items: [] })),
			invoiceApi
				.listInvoices(fetch, token, { project_id: params.id, page_size: 100 })
				.catch(() => ({ items: [] }))
		]);

		const activeSvcIds = project.services
			.filter((s) => s.status === 'active')
			.map((s) => s.service_id);
		const seen = new Set();
		const uniqueSvcIds = activeSvcIds.filter((id) => {
			if (seen.has(id)) return false;
			seen.add(id);
			return true;
		});
		const detailResults = await Promise.all(
			uniqueSvcIds.map((id) =>
				serviceApi
					.getService(fetch, token, id)
					.then((d) => ({ id, name: d.name, steps: d.steps ?? [] }))
					.catch(() => null)
			)
		);
		const serviceDetails = {};
		for (const r of detailResults) {
			if (r) serviceDetails[r.id] = r;
		}

		return { project, users: users.items, serviceDetails, overview, ledger, draftInvoices, invoices };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Project not found');
		}
		throw e;
	}
}
