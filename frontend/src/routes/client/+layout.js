import { redirect } from '@sveltejs/kit';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

// Public client routes that don't need auth
const PUBLIC_ROUTES = [
	'/client/login',
	'/client/accept-invite',
	'/client/forgot-password',
	'/client/reset-password'
];

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	// Skip guard for public routes
	if (PUBLIC_ROUTES.some((r) => url.pathname === r || url.pathname.startsWith(r + '/'))) {
		return;
	}
	await portalAuth.init(fetch);
	if (!portalAuth.user || !portalAuth.isClientUser) redirect(307, '/client/login');
}
