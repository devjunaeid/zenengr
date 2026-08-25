import { redirect } from '@sveltejs/kit';
import * as rolesApi from '$lib/api/roles.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	await auth.init(fetch);
	if (!auth.can('manage', 'roles')) redirect(307, '/app');

	const token = auth.token;
	const [roles, catalog] = await Promise.all([
		rolesApi.getRoles(fetch, token).catch(() => []),
		rolesApi.getPermissionCatalog(fetch, token).catch(() => [])
	]);
	return { roles, catalog };
}
