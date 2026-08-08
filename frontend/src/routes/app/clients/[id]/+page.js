import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as clientApi from '$lib/api/clients.js';
import { auth } from '$lib/stores/auth.svelte.js';

/**
 * Overview tab data. The client itself is loaded by the parent layout
 * ([id]/+layout.js) and shared across the tabs via the merged `data` prop.
 *
 * @param {{ fetch: typeof fetch, params: { id: string }, url: URL }} event
 */
export async function load({ fetch, params, url }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);
	const id = params.id;

	const notesPage = Math.max(1, Number(url.searchParams.get('notes_page') ?? '1') || 1);
	const activityPage = Math.max(1, Number(url.searchParams.get('activity_page') ?? '1') || 1);

	try {
		const [notes, activity, ledger, invites] = await Promise.all([
			clientApi.listNotes(fetch, token, id, { page: notesPage, page_size: 20 }),
			clientApi.listActivity(fetch, token, id, { page: activityPage, page_size: 20 }),
			clientApi.getClientLedger(fetch, token, id).catch(() => null),
			clientApi.listClientInvites(fetch, token, id).catch(() => [])
		]);
		return { notes, activity, ledger, invites, filters: { notesPage, activityPage } };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Client not found');
		}
		throw e;
	}
}
