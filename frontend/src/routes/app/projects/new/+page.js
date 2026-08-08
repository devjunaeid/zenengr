import * as clientApi from '$lib/api/clients.js';
import * as projectApi from '$lib/api/projects.js';
import * as serviceApi from '$lib/api/services.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	const [clients, services, users] = await Promise.all([
		clientApi.listClients(fetch, token, { page_size: 100, status: 'active' }),
		serviceApi.listServices(fetch, token, { page_size: 100, is_active: true }),
		tenantApi.listUsers(fetch, token, { page_size: 100, is_active: true })
	]);

	// For the preview-milestones feature, fetch full service details lazily
	// on the client (per selected service). The list response only carries
	// step_count, not the ordered step list.
	void projectApi; // silence unused import — kept for symmetry

	return {
		clients: clients.items,
		services: services.items,
		users: users.items,
		// Support ?client_id= deep link from a client's "New project" CTA.
		initialClientId: url.searchParams.get('client_id') ?? ''
	};
}
