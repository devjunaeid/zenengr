import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	const projects = await projectApi.listProjects(fetch, token, { page_size: 100 });

	return {
		projects: projects.items,
		// Support ?project_id=... deep link from a project's "New invoice" CTA.
		initialProjectId: url.searchParams.get('project_id') ?? ''
	};
}
