import { redirect } from '@sveltejs/kit';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	if (!auth.isTenantAdmin) redirect(307, '/app');

	const action = url.searchParams.get('action') ?? '';
	const from = url.searchParams.get('from') ?? '';
	const to = url.searchParams.get('to') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const audit = await tenantApi.getAuditLogs(fetch, auth.token, {
		page,
		page_size: 20,
		action,
		from,
		to
	});
	return { audit, filters: { action, from, to, page } };
}
