import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as projectApi from '$lib/api/projects.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = auth.token;

	try {
		const [project, users] = await Promise.all([
			projectApi.getProject(fetch, token, params.id),
			tenantApi
				.listUsers(fetch, token, { page_size: 100, is_active: true })
				.catch(() => ({ items: [] }))
		]);
		return { project, users: users.items };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Project not found');
		}
		throw e;
	}
}
