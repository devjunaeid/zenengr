import * as tenantApi from '$lib/api/tenant.js';
import { requireRole } from '$lib/guards.js';
import { auth } from '$lib/stores/auth.svelte.js';
import { setTenantSettings } from '$lib/stores/settings.svelte.js';

let cachedProfile = null;
let cachedSettingsLoaded = false;

export async function load({ fetch }) {
	const user = await requireRole(fetch, ['admin', 'manager', 'employee']);
	if (!cachedProfile) {
		try {
			cachedProfile = await tenantApi.getProfile(fetch, auth.token);
		} catch {
			cachedProfile = { business_name: 'ZenEngr' };
		}
	}
	await loadTenantSettings(fetch);
	return { user, profile: cachedProfile };
}

async function loadTenantSettings(fetch) {
	try {
		const rows = await tenantApi.getSettings(fetch, auth.token);
		const pick = (key) => rows.find((r) => r.key === key)?.value ?? undefined;
		setTenantSettings({
			currency: pick('currency'),
			timezone: pick('timezone'),
			date_format: pick('date_format'),
			time_format: pick('time_format'),
			invoice_prefix: pick('invoice_prefix'),
			invoice_number_format: pick('invoice_number_format')
		});
	} catch {
		// Settings unreachable — keep store defaults.
	}
}
