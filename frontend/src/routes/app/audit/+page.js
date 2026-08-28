import * as tenantApi from '$lib/api/tenant.js';
import { requireRole } from '$lib/guards.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	const user = await requireRole(fetch, ['admin']);

	const rawAction = url.searchParams.get('action')?.trim() || '';
	const rawFrom = url.searchParams.get('from')?.trim() || '';
	const rawTo = url.searchParams.get('to')?.trim() || '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const params = {
		page,
		page_size: 20
	};
	if (rawAction) params.action = rawAction;
	if (rawFrom) params.from = rawFrom;
	if (rawTo) params.to = rawTo;

	try {
		const audit = await tenantApi.getAuditLogs(fetch, auth.token, params);
		return {
			user,
			audit,
			filters: { action: rawAction, from: rawFrom, to: rawTo, page }
		};
	} catch (e) {
		return {
			user,
			audit: { items: [], total: 0, page: 1, page_size: 20 },
			filters: { action: rawAction, from: rawFrom, to: rawTo, page },
			error: e?.message || 'Failed to load audit logs'
		};
	}
}
