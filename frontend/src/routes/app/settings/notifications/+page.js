import * as accountApi from '$lib/api/account.js';
import { requireRole } from '$lib/guards.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	const user = await requireRole(fetch, ['admin', 'manager', 'employee']);
	const token = /** @type {string} */ (auth.token);
	const [prefs, inappPrefs] = await Promise.all([
		accountApi.getNotificationPreferences(fetch, token, { realm: 'admin' }),
		accountApi.getNotificationPreferences(fetch, token, { realm: 'admin', channel: 'inapp' })
	]);
	return { user, prefs, inappPrefs };
}
