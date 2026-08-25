import * as clientApi from '$lib/api/clients.js';
import * as serviceApi from '$lib/api/services.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const [clients, services, users] = await Promise.all([
		clientApi.listClients(fetch, token, { page_size: 100, status: 'active' }),
		serviceApi.listServices(fetch, token, { page_size: 100, is_active: true }),
		tenantApi.listUsers(fetch, token, { page_size: 100, is_active: true })
	]);

	return {
		clients: clients.items,
		services: services.items,
		users: users.items,
		initialClientId: url.searchParams.get('client_id') ?? ''
	};
}
