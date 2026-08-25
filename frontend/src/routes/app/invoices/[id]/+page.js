import { error } from '@sveltejs/kit';
import { ApiError } from '$lib/api/client.js';
import * as invoiceApi from '$lib/api/invoices.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch, params }) {
	await auth.init(fetch);
	const token = auth.token;

	try {
		const [invoice, transactions] = await Promise.all([
			invoiceApi.getInvoice(fetch, token, params.id),
			invoiceApi.listTransactions(fetch, token, params.id).catch(() => [])
		]);
		return { invoice, transactions };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			throw error(404, 'Invoice not found');
		}
		throw e;
	}
}
