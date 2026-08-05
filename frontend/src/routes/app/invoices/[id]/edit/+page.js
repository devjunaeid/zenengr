import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch, params: { id: string } }} event */
export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	try {
		const invoice = await invoiceApi.getInvoice(fetch, token, params.id);
		// General (internal) invoices have no project; the edit page renders
		// custom line items only in that case.
		const project = invoice.project_id
			? await projectApi.getProject(fetch, token, invoice.project_id)
			: null;
		return { invoice, project };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Invoice not found');
		}
		throw e;
	}
}
