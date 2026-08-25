import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const projects = await projectApi.listProjects(fetch, token, { page_size: 100 });

	return {
		projects: projects.items,
		initialProjectId: url.searchParams.get('project_id') ?? ''
	};
}
