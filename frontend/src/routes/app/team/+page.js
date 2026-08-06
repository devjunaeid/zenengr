import * as rolesApi from '$lib/api/roles.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);
	const [users, invites, roles] = await Promise.all([
		tenantApi.listUsers(fetch, token, { page_size: 100 }),
		tenantApi.listInvites(fetch, token),
		rolesApi.getRoles(fetch, token).catch(() => [])
	]);
	return { users, invites, roles };
}
