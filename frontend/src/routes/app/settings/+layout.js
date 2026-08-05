import { requireRole } from '$lib/guards.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	// Settings is an admin/manager staff area (the app-shell nav hides it from
	// employees via adminOnly, but the guard below is the enforcement point for
	// all settings subroutes). The parent /app layout already guards the realm;
	// this is a defensive re-check.
	await requireRole(fetch, ['admin', 'manager']);
}
