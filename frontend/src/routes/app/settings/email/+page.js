import * as smtpApi from '$lib/api/smtp.js';
import { auth } from '$lib/stores/auth.svelte.js';

export async function load({ fetch }) {
	await auth.init(fetch);
	const token = auth.token;

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
		// Keep defaults if unconfigured
	}
	return { config };
}
