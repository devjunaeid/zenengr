import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);
	const [profile, settings] = await Promise.all([
		tenantApi.getProfile(fetch, token),
		tenantApi.getSettings(fetch, token)
	]);
	return { profile, settings };
}
