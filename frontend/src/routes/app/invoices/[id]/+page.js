import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as invoiceApi from '$lib/api/invoices.js';
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
		return { invoice, transactions, profile };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Invoice not found');
		}
		throw e;
	}
}
