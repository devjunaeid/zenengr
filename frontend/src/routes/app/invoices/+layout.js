import { requireRole } from '$lib/guards.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	// Tenant-staff guard for all /app/invoices subroutes. The parent /app
	// layout already guards the realm; this is a defensive re-check.
	await requireRole(fetch, ['admin', 'manager', 'employee']);
}
