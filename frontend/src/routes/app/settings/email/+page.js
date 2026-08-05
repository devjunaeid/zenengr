import * as smtpApi from '$lib/api/smtp.js';
import { auth } from '$lib/stores/auth.svelte.js';

/** @param {{ fetch: typeof fetch }} event */
export async function load({ fetch }) {
	await auth.init(fetch);
	const token = /** @type {string} */ (auth.token);

	/** @type {import('$lib/api/smtp.js').SmtpConfig} */
	let config = {
		host: '',
		port: 587,
		username: '',
		from_email: '',
		from_name: '',
		mode: 'none',
		enabled: false,
		has_password: false
	};
	try {
		config = await smtpApi.getSmtpConfig(fetch, token);
	} catch {
		// No configuration yet (or backend unavailable): keep defaults so the
		// form still renders; the save flow surfaces real errors.
	}
	return { config };
}
