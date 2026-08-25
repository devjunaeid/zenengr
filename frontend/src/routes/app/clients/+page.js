import * as clientApi from '$lib/api/clients.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const q = url.searchParams.get('q') ?? '';
	const status = url.searchParams.get('status') ?? '';
	const tag = url.searchParams.get('tag') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	const [clients, tagsRes] = await Promise.all([
		clientApi.listClients(fetch, token, { page, page_size: 20, status, q, tag }),
		clientApi.listTags(fetch, token)
	]);

	return { clients, tags: tagsRes.tags, filters: { q, status, tag, page } };
}
