import * as clientApi from '$lib/api/clients.js';
import * as serviceApi from '$lib/api/services.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const initialClientId = url.searchParams.get('client_id') ?? '';

	const [clients, services, users] = await Promise.all([
		clientApi.getClientPicker(fetch, token, { status: 'active', limit: 20 }),
		serviceApi.listServices(fetch, token, { page_size: 100, is_active: true }),
		tenantApi.listUsers(fetch, token, { page_size: 100, is_active: true })
	]);

	return {
		clients: clients.items,
		services: services.items,
		users: users.items,
		initialClientId
	};
}
