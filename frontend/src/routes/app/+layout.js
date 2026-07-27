import * as tenantApi from '$lib/api/tenant.js';
import { requireRole } from '$lib/guards.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	const user = await requireRole(fetch, ['admin', 'manager', 'employee']);
	const profile = await tenantApi.getProfile(fetch, /** @type {string} */ (auth.token));
	return { user, profile };
}
