import * as filesApi from '$lib/api/files.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const folderId = url.searchParams.get('folder_id') ?? '';
	const scope = url.searchParams.get('scope') ?? 'user';
	const projectId = url.searchParams.get('project_id') ?? '';
	const q = url.searchParams.get('q') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const [folders, files, projects] = await Promise.all([
		filesApi.listFolders(fetch, token).catch(() => []),
		filesApi
			.listFiles(fetch, token, {
				...(folderId && { folder_id: folderId }),
				scope,
				...(projectId && { project_id: projectId }),
				...(q && { q }),
				page,
				page_size: 20
			})
			.catch(() => ({ items: [], total: 0, page: 1, page_size: 20 })),
		projectApi.listProjects(fetch, token, { page_size: 100 }).catch(() => ({ items: [] }))
	]);

	return {
		folders,
		files,
		projects: projects.items,
		filters: { folder_id: folderId, scope, project_id: projectId, q, page }
	};
}
