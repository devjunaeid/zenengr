import { redirect } from '@sveltejs/kit';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await portalAuth.init(fetch);
	if (portalAuth.user && portalAuth.isClientUser) redirect(307, '/client');
}
