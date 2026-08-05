import * as filesApi from '$lib/api/files.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, url: URL }} event */
export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	const folderId = url.searchParams.get('folder_id') ?? '';
	// Absent folder_id + scope user = the virtual "My files" root.
	const scope = url.searchParams.get('scope') ?? 'user';
	const projectId = url.searchParams.get('project_id') ?? '';
	const q = url.searchParams.get('q') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const [folders, files, projects] = await Promise.all([
		// Failures degrade to empty lists so the page still renders.
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
