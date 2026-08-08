import { requireRole } from '$lib/guards.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	// Settings is a staff area (the app-shell nav hides it from employees via
	// permissions, but the guard below is the enforcement point for all settings
	// subroutes). The parent /app layout already guards the realm; this is a
	// defensive re-check. Services is staff-viewable; other tabs' content stays
	// gated by permission in the UI and on the server.
	await requireRole(fetch, ['admin', 'manager', 'employee']);
}
