import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	await auth.init(fetch);
	const token = auth.token;
	const [plan, flags, profile] = await Promise.all([
		tenantApi.getPlan(fetch, token),
		tenantApi.getFlags(fetch, token),
		tenantApi.getProfile(fetch, token)
	]);
	return { plan, flags, profile };
}
