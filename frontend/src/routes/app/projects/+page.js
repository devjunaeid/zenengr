import * as projectApi from '$lib/api/projects.js';
import * as clientApi from '$lib/api/clients.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const q = url.searchParams.get('q') ?? '';
	const status = url.searchParams.get('status') ?? '';
	const clientId = url.searchParams.get('client_id') ?? '';
	const tag = url.searchParams.get('tag') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const [tagsRes, projects] = await Promise.all([
		clientApi.listTags(fetch, token).catch(() => ({ tags: [] })),
		projectApi.listProjects(fetch, token, {
			page,
			page_size: 20,
			...(status && { status }),
			...(clientId && { client_id: clientId }),
			...(tag && { tag }),
			...(q && { q })
		})
	]);

	const tags = Array.isArray(tagsRes?.tags) ? tagsRes.tags : [];
	return { projects, tags, filters: { q, status, client_id: clientId, tag, page } };
}
