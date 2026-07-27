import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	const plan = await tenantApi.getPlan(fetch, /** @type {string} */ (auth.token));
	return { plan };
}
