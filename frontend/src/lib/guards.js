import { redirect } from '@sveltejs/kit';
import { auth, homeForRole } from '$lib/stores/auth.svelte.js';

/**
 * Route guard for protected layout/page loads. Waits for session restore,
 * redirects unauthenticated users to /login and wrong-role users to their home.
 *
 * @param {typeof fetch} fetchFn event.fetch from the load function
 * @param {string[]} roles allowed roles
 * @returns {Promise<import('$lib/api/auth.js').AuthUser>} the authenticated user
 */
export async function requireRole(fetchFn, roles) {
	await auth.init(fetchFn);
	const user = auth.user;
	if (!user) redirect(307, '/login');
	if (!roles.includes(user.role)) redirect(307, homeForRole(user.role));
	return user;
}
