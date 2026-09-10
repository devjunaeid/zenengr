import * as clientApi from '$lib/api/clients.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;
	const initialProjectId = url.searchParams.get('project_id') ?? '';

	const [pickerRes, clientsRes, initialProject] = await Promise.all([
		projectApi.getProjectPicker(fetch, token, { limit: 10 }).catch(() => ({ items: [] })),
		clientApi.listClients(fetch, token, { page_size: 20 }).catch(() => ({ items: [] })),
		initialProjectId
			? projectApi.getProject(fetch, token, initialProjectId).catch(() => null)
			: null
	]);

	const projects = pickerRes.items ?? [];
	if (initialProject && !projects.some((p) => p.id === initialProject.id)) {
		projects.unshift({
			id: initialProject.id,
			name: initialProject.name,
			client_id: initialProject.client_id,
			status: initialProject.status,
			client_name: initialProject.client?.name ?? null
		});
	}

	return {
		projects,
		clients: clientsRes.items ?? [],
		initialProjectId
	};
}
