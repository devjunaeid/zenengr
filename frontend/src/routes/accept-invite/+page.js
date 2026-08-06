import * as authApi from '$lib/api/auth.js';

/**
 * @type {import('./$types').PageLoad}
 * @param {{ url: URL, fetch: typeof fetch }} event
 */
export async function load({ url, fetch }) {
	const token = url.searchParams.get('token');
	if (!token) {
		return { state: 'invalid', token: null, invite: null };
	}

	try {
		const invite = await authApi.getInvite(fetch, token);
		return { state: 'ready', token, invite };
	} catch (e) {
		if (e && typeof e === 'object' && 'status' in e) {
			if (e.status === 404) return { state: 'invalid', token, invite: null };
			if (e.status === 410) return { state: 'expired', token, invite: null };
			if (e.status === 409) return { state: 'accepted', token, invite: null };
		}
		return { state: 'invalid', token, invite: null };
	}
}
