import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

/**
 * Projects tab: the given client's projects, paginated. The client record
 * itself comes from the parent layout ([id]/+layout.js).
 *
 * @param {{ fetch: typeof fetch, params: { id: string }, url: URL }} event
 */
export async function load({ fetch, params, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const projects = await projectApi.listProjects(fetch, token, {
		page,
		page_size: 20,
		client_id: params.id
	});

	return { projects };
}
