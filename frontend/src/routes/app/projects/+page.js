import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	const q = url.searchParams.get('q') ?? '';
	const status = url.searchParams.get('status') ?? '';
	const clientId = url.searchParams.get('client_id') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const projects = await projectApi.listProjects(fetch, token, {
		page,
		page_size: 20,
		...(status && { status }),
		...(clientId && { client_id: clientId }),
		...(q && { q })
	});

	return { projects, filters: { q, status, client_id: clientId, page } };
}
