import * as adminApi from '$lib/api/admin.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	await auth.init(fetch);
	const q = url.searchParams.get('q') ?? '';
	const status = url.searchParams.get('status') ?? '';
	const sort = url.searchParams.get('sort') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);
	const data = await adminApi.listTenants(fetch, /** @type {string} */ (auth.token), {
		page,
		page_size: 20,
		status,
		q,
		sort
	});
	return { tenants: data, filters: { q, status, sort, page } };
}
