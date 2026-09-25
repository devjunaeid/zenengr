import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as clientsApi from '$lib/api/clients.js';
import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = auth.token;

	try {
		const projectPromise = projectApi.getProject(fetch, token, params.id);
		const clientPromise = projectPromise
			.then((p) =>
				p?.client_id ? clientsApi.getClient(fetch, token, p.client_id).catch(() => null) : null
			)
			.catch(() => null);

		const [project, client, overview] = await Promise.all([
			projectPromise,
			clientPromise,
			invoiceApi.getProjectOverview(fetch, token, params.id).catch(() => null)
		]);

		const serviceDetails = {};
		for (const s of project.services ?? []) {
			serviceDetails[s.service_id] = { id: s.service_id, name: s.service_name, steps: [] };
		}

		return {
			project,
			client,
			overview,
			serviceDetails,
			users: [],
			ledger: null,
			draftInvoices: { items: [] },
			invoices: { items: [], total: 0 },
			projectFiles: [],
			folderTree: [],
			projectRoles: []
		};
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Project not found');
		}
		throw e;
	}
}
