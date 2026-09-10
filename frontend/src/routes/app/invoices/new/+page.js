import * as clientApi from '$lib/api/clients.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const [projects, clients] = await Promise.all([
		projectApi.listProjects(fetch, token, { page_size: 100 }).catch(() => ({ items: [] })),
		clientApi.listClients(fetch, token, { page_size: 100 }).catch(() => ({ items: [] }))
	]);

	return {
		projects: projects.items,
		clients: clients.items,
		initialProjectId: url.searchParams.get('project_id') ?? ''
	};
}
