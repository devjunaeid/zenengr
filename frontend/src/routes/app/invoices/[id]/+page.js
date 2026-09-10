import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as invoiceApi from '$lib/api/invoices.js';
import * as projectApi from '$lib/api/projects.js';
import * as tenantApi from '$lib/api/tenant.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = auth.token;

	try {
		const [invoice, transactions, profile] = await Promise.all([
			invoiceApi.getInvoice(fetch, token, params.id),
			invoiceApi.listTransactions(fetch, token, params.id).catch(() => []),
			tenantApi.getProfile(fetch, token).catch(() => null)
		]);
		const project = invoice.project_id
			? await projectApi.getProject(fetch, token, invoice.project_id).catch(() => null)
			: null;
		return { invoice, transactions, profile, project };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Invoice not found');
		}
		throw e;
	}
}
