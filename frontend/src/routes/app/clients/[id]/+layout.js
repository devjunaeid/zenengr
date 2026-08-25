import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as clientApi from '$lib/api/clients.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = auth.token;

	try {
		const client = await clientApi.getClient(fetch, token, params.id);
		return { client };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Client not found');
		}
		throw e;
	}
}
