import * as clientApi from '$lib/api/clients.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	await auth.init(fetch);
	const token = auth.token;
	const tagsSummary = await clientApi.getTagsSummary(fetch, token).catch(() => ({ items: [] }));
	return { tags: tagsSummary.items ?? [] };
}
