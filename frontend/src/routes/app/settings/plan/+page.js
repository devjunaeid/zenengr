import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);
	const [plan, flags, profile] = await Promise.all([
		tenantApi.getPlan(fetch, token),
		tenantApi.getFlags(fetch, token),
		tenantApi.getProfile(fetch, token)
	]);
	return { plan, flags, profile };
}
