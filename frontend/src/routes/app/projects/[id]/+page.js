import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import * as serviceApi from '$lib/api/services.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, params: { id: string } }} event */
export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	try {
		const [project, users, overview, ledger] = await Promise.all([
			projectApi.getProject(fetch, token, params.id),
			tenantApi
				.listUsers(fetch, token, { page_size: 100, is_active: true })
				.catch(() => ({ items: [] })),
			// Financial summary is a nice-to-have on this page; a failure here
			// must not take down the whole project view.
			invoiceApi.getProjectOverview(fetch, token, params.id).catch(() => null),
			// Same for the ledger: degrade to null and let the section render
			// its "unavailable" state.
			projectApi.getProjectLedger(fetch, token, params.id).catch(() => null)
		]);

		// Fetch active service details so we can show step previews when adding
		// a service. Cancel failures silently — preview is a nice-to-have.
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
		/** @type {Record<string, { id: string, name: string, steps: import('$lib/api/services.js').MilestoneStep[] }>} */
		const serviceDetails = {};
		for (const r of detailResults) {
			if (r) serviceDetails[r.id] = r;
		}

		return { project, users: users.items, serviceDetails, overview, ledger };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Project not found');
		}
		throw e;
	}
}
