import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as portalApi from '$lib/api/portal.js';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

/** @param {{ fetch: typeof fetch, params: { id: string } }} event */
export async function load({ fetch, params }) {
	await portalAuth.init(fetch);
	const token = /** @type {string} */ (portalAuth.token);

	try {
		const [project, ledger] = await Promise.all([
			portalApi.getClientProject(fetch, token, params.id),
			// Read-only ledger degrades to null on failure; the page renders an
			// "unavailable" state instead of failing the whole project view.
			portalApi.getClientProjectLedger(fetch, token, params.id).catch(() => null)
		]);
		// Files degrade to an empty list on failure; the page shows a banner.
		/** @type {string|null} */
		let filesError = null;
		/** @type {{ items: any[], total: number, page: number, page_size: number }} */
		let files;
		try {
			files = await portalApi.listClientProjectFiles(fetch, token, params.id, { page_size: 50 });
		} catch (e) {
			files = { items: [], total: 0, page: 1, page_size: 50 };
			filesError = e instanceof ApiError ? e.message : 'Could not load project files.';
		}
		return { project, files, filesError, ledger };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Project not found');
		}
		throw e;
	}
}
