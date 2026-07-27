import { redirect } from '@sveltejs/kit';
import { auth, homeForRole } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	redirect(307, auth.user ? homeForRole(auth.user.role) : '/login');
}
