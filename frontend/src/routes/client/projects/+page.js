import * as portalApi from '$lib/api/portal.js';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	await portalAuth.init(fetch);
	const token = /** @type {string} */ (portalAuth.token);

	const status = url.searchParams.get('status') ?? '';
	const q = url.searchParams.get('q') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const projects = await portalApi.listClientProjects(fetch, token, {
		page,
		page_size: 20,
		...(status && { status }),
		...(q && { q })
	});

	return { projects, filters: { status, q, page } };
}
