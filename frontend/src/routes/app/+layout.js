import * as tenantApi from '$lib/api/tenant.js';
import { requireRole } from '$lib/guards.js';
import { auth } from '$lib/stores/auth.svelte.js';
import { setTenantSettings } from '$lib/stores/settings.svelte.js';

export async function load({ fetch, depends }) {
	depends('app:profile');
	const user = await requireRole(fetch, ['admin', 'manager', 'employee']);
	let profile = { business_name: 'ZenEngr' };
	try {
		profile = await tenantApi.getProfile(fetch, auth.token);
	} catch {
		profile = { business_name: 'ZenEngr' };
	}
	await loadTenantSettings(fetch);
	return { user, profile };
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
