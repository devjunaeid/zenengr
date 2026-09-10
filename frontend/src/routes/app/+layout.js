import * as tenantApi from '$lib/api/tenant.js';
import { requireRole } from '$lib/guards.js';
import { auth } from '$lib/stores/auth.svelte.js';
import { setTenantSettings } from '$lib/stores/settings.svelte.js';

export async function load({ fetch, depends }) {
	depends('app:profile');
	const user = await requireRole(fetch, ['admin', 'manager', 'employee']);

	const [profile, settingsRows] = await Promise.all([
		tenantApi.getProfile(fetch, auth.token).catch(() => ({ business_name: 'ZenEngr' })),
		tenantApi.getSettings(fetch, auth.token).catch(() => [])
	]);

	applyTenantSettings(settingsRows);
	return { user, profile };
}

function applyTenantSettings(rows) {
	if (!Array.isArray(rows) || rows.length === 0) return;
	const pick = (key) => rows.find((r) => r.key === key)?.value ?? undefined;
	setTenantSettings({
		currency: pick('currency'),
		timezone: pick('timezone'),
		date_format: pick('date_format'),
		time_format: pick('time_format'),
		invoice_prefix: pick('invoice_prefix'),
		invoice_number_format: pick('invoice_number_format')
	});
}
