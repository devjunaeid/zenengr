import { requireRole } from '$lib/guards.js';

export async function load({ fetch }) {
	await requireRole(fetch, ['admin', 'manager', 'employee']);
}
