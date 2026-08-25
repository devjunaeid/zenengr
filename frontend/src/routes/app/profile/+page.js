import * as accountApi from '$lib/api/account.js';
import { requireRole } from '$lib/guards.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	const user = await requireRole(fetch, ['admin', 'manager', 'employee']);
	const token = auth.token;
	const [profile, activity] = await Promise.all([
		accountApi.getMe(fetch, token, { realm: 'admin' }),
		accountApi.getActivity(fetch, token, { realm: 'admin' })
	]);
	return { user, profile, activity };
}
