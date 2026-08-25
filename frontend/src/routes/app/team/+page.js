import * as rolesApi from '$lib/api/roles.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	await auth.init(fetch);
	const token = auth.token;
	const [users, invites, roles] = await Promise.all([
		tenantApi.listUsers(fetch, token, { page_size: 100 }),
		tenantApi.listInvites(fetch, token),
		rolesApi.getRoles(fetch, token).catch(() => [])
	]);
	return { users, invites, roles };
}
