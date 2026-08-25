import * as serviceApi from '$lib/api/services.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, url }) {
	await auth.init(fetch);
	const token = auth.token;

	const q = url.searchParams.get('q') ?? '';
	const isActiveRaw = url.searchParams.get('is_active') ?? '';
	const page = Math.max(1, Number(url.searchParams.get('page') ?? '1') || 1);

	let isActiveParam;
	if (isActiveRaw === 'active') isActiveParam = true;
	else if (isActiveRaw === 'inactive') isActiveParam = false;

	const services = await serviceApi.listServices(fetch, token, {
		page,
		page_size: 20,
		...(isActiveParam !== undefined && { is_active: isActiveParam }),
		...(q && { q })
	});

	return { services, filters: { q, is_active: isActiveRaw, page } };
}
