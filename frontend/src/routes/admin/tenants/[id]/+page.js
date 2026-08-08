import * as adminApi from '$lib/api/admin.js';
import { ApiError } from '$lib/api/client.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, params: Record<string, string>, url: URL }} event */
export async function load({ fetch, params, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);
	const id = params.id;
	const auditPage = Math.max(1, Number(url.searchParams.get('apage') ?? '1') || 1);
	const auditAction = url.searchParams.get('action') ?? '';

	const [tenant, plans, flags, audit, settings] = await Promise.all([
		adminApi.getTenant(fetch, token, id),
		adminApi.listPlans(fetch, token),
		adminApi.getFlags(fetch, token, id),
		adminApi.getAuditLogs(fetch, token, id, {
			page: auditPage,
			page_size: 20,
			action: auditAction
		}),
		adminApi.getTenantSettings(fetch, token, id)
	]);

	// Subscription is optional; 404 means none exists yet.
	let subscription = null;
	try {
		subscription = await adminApi.getSubscription(fetch, token, id);
	} catch (e) {
		if (!(e instanceof ApiError && e.status === 404)) throw e;
	}

	return { tenant, plans, flags, subscription, audit, settings, auditAction };
}
