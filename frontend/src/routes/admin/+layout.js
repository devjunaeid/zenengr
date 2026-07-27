import { requireRole } from '$lib/guards.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await requireRole(fetch, ['super_admin']);
}
