import { redirect } from '@sveltejs/kit';
import { auth, homeForRole } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	if (auth.user) redirect(307, homeForRole(auth.user.role));
}
