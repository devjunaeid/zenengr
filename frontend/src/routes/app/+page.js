import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	await auth.init(fetch);
	const plan = await tenantApi.getPlan(fetch, auth.token);
	return { plan };
}
