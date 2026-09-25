import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as portalApi from '$lib/api/portal.js';
import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

/** @param {{ fetch: typeof fetch, params: { id: string }, url: URL }} event */
export async function load({ fetch, params, url }) {
	await portalAuth.init(fetch);
	const token = /** @type {string} */ (portalAuth.token);

	const tab = url.searchParams.get('tab') || 'overview';

	try {
		const project = await portalApi.getClientProject(fetch, token, params.id);
		let ledger = null;
		let files = { items: [], total: 0, page: 1, page_size: 50 };
		let filesError = null;

		if (tab === 'financials') {
			ledger = await portalApi.getClientProjectLedger(fetch, token, params.id).catch(() => null);
		} else if (tab === 'files') {
			try {
				files = await portalApi.listClientProjectFiles(fetch, token, params.id, { page_size: 50 });
			} catch (e) {
				filesError = e instanceof ApiError ? e.message : 'Could not load project files.';
			}
		}

		return { project, files, filesError, ledger };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Project not found');
		}
		throw e;
	}
}
