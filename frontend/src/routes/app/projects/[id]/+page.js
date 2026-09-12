import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as clientsApi from '$lib/api/clients.js';
import * as filesApi from '$lib/api/files.js';
import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import * as rolesApi from '$lib/api/roles.js';
import * as tenantApi from '$lib/api/tenant.js';
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

		const [
			project,
			client,
			users,
			overview,
			ledger,
			invoices,
			projectFiles,
			folderTree,
			projectRoles
		] = await Promise.all([
			projectPromise,
			clientPromise,
			tenantApi
				.listUsers(fetch, token, { page_size: 100, is_active: true })
				.catch(() => ({ items: [] })),
			invoiceApi.getProjectOverview(fetch, token, params.id).catch(() => null),
			projectApi.getProjectLedger(fetch, token, params.id).catch(() => null),
			invoiceApi
				.listInvoices(fetch, token, { project_id: params.id, page_size: 100 })
				.catch(() => ({ items: [] })),
			filesApi
				.listFiles(fetch, token, { project_id: params.id, scope: 'project', page_size: 100 })
				.catch(() => ({ items: [], total: 0 })),
			filesApi.listFolders(fetch, token).catch(() => []),
			rolesApi.getRoles(fetch, token).catch(() => [])
		]);

		const serviceDetails = {};
		for (const s of project.services ?? []) {
			serviceDetails[s.service_id] = { id: s.service_id, name: s.service_name, steps: [] };
		}

		const draftInvoices = {
			items: (invoices.items ?? []).filter((inv) => inv.status === 'draft').slice(0, 5)
		};

		return {
			project,
			client,
			users: users.items,
			serviceDetails,
			overview,
			ledger,
			draftInvoices,
			invoices,
			projectFiles: projectFiles.items ?? [],
			folderTree,
			projectRoles: (projectRoles ?? []).filter((r) => r.role_type === 'project')
		};
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Project not found');
		}
		throw e;
	}
}
