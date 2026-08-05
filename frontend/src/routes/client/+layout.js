import { redirect } from '@sveltejs/kit';
import { apiFetch } from '$lib/api/client.js';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
import { setTenantSettings } from '$lib/stores/settings.svelte.js';

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
	await loadTenantSettings(fetch);
}

/** @param {typeof fetch} fetch */
async function loadTenantSettings(fetch) {
	try {
		const s = await apiFetch(fetch, '/client/settings', {
			token: /** @type {string} */ (portalAuth.token)
		});
		setTenantSettings({
			currency: s?.currency,
			timezone: s?.timezone,
			date_format: s?.date_format,
			time_format: s?.time_format
		});
	} catch {
		// Settings unreachable — keep store defaults.
	}
}
