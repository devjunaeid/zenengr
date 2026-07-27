import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);
	const [users, invites] = await Promise.all([
		tenantApi.listUsers(fetch, token, { page_size: 100 }),
		tenantApi.listInvites(fetch, token)
	]);
	return { users, invites };
}
