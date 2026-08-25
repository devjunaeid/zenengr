import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	await auth.init(fetch);
	const token = auth.token;
	const profile = await tenantApi.getProfile(fetch, token);
	return { profile };
}
