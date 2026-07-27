import * as adminApi from '$lib/api/admin.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	const plans = await adminApi.listPlans(fetch, /** @type {string} */ (auth.token));
	return { plans: plans.filter((p) => p.is_active) };
}
