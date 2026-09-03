<script>
	import { invalidateAll } from '$app/navigation';
	import { untrack } from 'svelte';
	import { ApiError } from '$lib/api/client.js';
	import * as smtpApi from '$lib/api/smtp.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import Icon from '@iconify/svelte';
	import emailCheck from '@iconify-icons/mdi/email-check';
	import serverSecurity from '@iconify-icons/mdi/server-security';
	import sendOutline from '@iconify-icons/mdi/send-outline';
	import accountLock from '@iconify-icons/mdi/account-lock';

	let { data } = $props();

	const token = auth.token;
	const initial = untrack(() => data.config);

	let enabled = $state(initial.enabled);
	let host = $state(initial.host);
	let port = $state(initial.port);
	let username = $state(initial.username);
	let password = $state('');
	let fromEmail = $state(initial.from_email);
	let fromName = $state(initial.from_name);
	let mode = $state(initial.mode);
	let hasPassword = $state(initial.has_password);
	let clearPassword = $state(false);

	let saving = $state(false);
	let saveMsg = $state(null);
	let saveErr = $state(null);

	let testing = $state(false);
	let testMsg = $state(null);
	let testErr = $state(null);

	async function saveSmtp() {
		saveMsg = null;
		saveErr = null;
		if (enabled && (!host.trim() || !fromEmail.trim())) {
			saveErr = 'Host and From Email are required when SMTP delivery is enabled.';
			return;
		}
		saving = true;
		try {
			const payload = {
				enabled,
				host: host.trim(),
				port,
				username: (username ?? '').trim() === '' ? null : (username ?? '').trim(),
				from_email: fromEmail.trim(),
				from_name: fromName.trim(),
				mode
			};
			if (password !== '' && !clearPassword) payload.password = password;
			if (clearPassword) payload.clear_password = true;
			const updated = await smtpApi.updateSmtpConfig(fetch, token, payload);
			enabled = updated.enabled;
			host = updated.host;
			port = updated.port;
			username = updated.username;
			fromEmail = updated.from_email;
			fromName = updated.from_name;
			mode = updated.mode;
			hasPassword = updated.has_password;
			password = '';
			clearPassword = false;
			saveMsg = 'SMTP settings saved successfully.';
			setTimeout(() => (saveMsg = null), 3000);
			await invalidateAll();
		} catch (e) {
			saveErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			saving = false;
		}
	}

	async function sendTest() {
		testMsg = null;
		testErr = null;
		testing = true;
		try {
			const res = await smtpApi.testSmtpConfig(fetch, token);
			testMsg = res.message;
		} catch (e) {
			testErr = e instanceof ApiError ? e.message : 'Test email failed. Check your credentials.';
		} finally {
			testing = false;
		}
	}
</script>

<svelte:head><title>Email (SMTP) — ZenEngr</title></svelte:head>

<div class="space-y-6">
	{#if saveMsg}
		<div
			role="status"
			class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-800 shadow-2xs"
		>
			✓ {saveMsg}
		</div>
	{/if}
	{#if saveErr}
		<div
			role="alert"
			class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs font-semibold text-red-800 shadow-2xs"
		>
			{saveErr}
		</div>
	{/if}

	<form
		onsubmit={(e) => {
			e.preventDefault();
			saveSmtp();
		}}
		class="space-y-6"
	>
		<!-- SMTP Delivery Status Card -->
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
				<div class="flex items-center gap-3">
					<div
						class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl {enabled
							? 'bg-indigo-50 text-indigo-600'
							: 'bg-slate-100 text-slate-400'}"
					>
						<Icon icon={emailCheck} class="h-5 w-5" />
					</div>
					<div>
						<h2 class="text-sm font-bold text-slate-900">Custom SMTP Delivery</h2>
						<p class="text-xs text-slate-500">
							Route all transactional client invitations, invoice notifications, and resets through
							your server.
						</p>
					</div>
				</div>

				<label class="relative inline-flex cursor-pointer items-center gap-3">
					<input type="checkbox" bind:checked={enabled} class="peer sr-only" />
					<div
						class="h-6 w-11 rounded-full bg-slate-200 transition-colors peer-checked:bg-indigo-600 peer-focus:ring-2 peer-focus:ring-indigo-500 peer-focus:ring-offset-2 after:absolute after:top-0.5 after:left-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-xs after:transition-all peer-checked:after:translate-x-full"
					></div>
					<span class="text-xs font-semibold text-slate-700">{enabled ? 'Active' : 'Disabled'}</span
					>
				</label>
			</div>
		</section>

		<!-- Server & Connection Card -->
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
					>
						<Icon icon={serverSecurity} class="h-4 w-4" />
					</div>
					<div>
						<h2 class="text-sm font-bold text-slate-900">Server Connection & Encryption</h2>
						<p class="text-xs text-slate-500">
							Host address, connection port, and TLS/SSL security mode.
						</p>
					</div>
				</div>
			</div>

			<div class="p-6">
				<div class="grid gap-5 sm:grid-cols-3">
					<div class="sm:col-span-2">
						<label
							for="smtp-host"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							SMTP Host / Server Address <span class="text-red-500">*</span>
						</label>
						<input
							id="smtp-host"
							type="text"
							bind:value={host}
							placeholder="smtp.mailgun.org or host.docker.internal"
							required={enabled}
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 font-mono text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div>
						<label
							for="smtp-port"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							Port Number <span class="text-red-500">*</span>
						</label>
						<input
							id="smtp-port"
							type="number"
							bind:value={port}
							min="1"
							max="65535"
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 font-mono text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div class="sm:col-span-3">
						<label
							for="smtp-mode"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							Security &amp; Encryption Mode
						</label>
						<select
							id="smtp-mode"
							bind:value={mode}
							class="mt-1.5 block w-full max-w-sm rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						>
							<option value="none">None (Plaintext / Local Dev)</option>
							<option value="starttls">STARTTLS (Port 587 / Modern Standard)</option>
							<option value="ssl">SSL / TLS (Port 465 / Direct Encrypted)</option>
						</select>
					</div>
				</div>
			</div>
		</section>

		<!-- Credentials & Sender Identity Card -->
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
					>
						<Icon icon={accountLock} class="h-4 w-4" />
					</div>
					<div>
						<h2 class="text-sm font-bold text-slate-900">Authentication & Sender Identity</h2>
						<p class="text-xs text-slate-500">
							Login credentials and the outgoing display name on outgoing emails.
						</p>
					</div>
				</div>
			</div>

			<div class="space-y-5 p-6">
				<div class="grid gap-5 sm:grid-cols-2">
					<div>
						<label
							for="smtp-username"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							SMTP Username
						</label>
						<input
							id="smtp-username"
							type="text"
							bind:value={username}
							autocomplete="off"
							placeholder="postmaster@yourdomain.com"
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div>
						<label
							for="smtp-password"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							SMTP Password
						</label>
						<input
							id="smtp-password"
							type="password"
							bind:value={password}
							disabled={clearPassword}
							placeholder={hasPassword ? '•••••••• (saved and encrypted)' : 'Enter password'}
							autocomplete="new-password"
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-400"
						/>
						{#if hasPassword}
							<label
								class="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs text-slate-600"
							>
								<input
									type="checkbox"
									bind:checked={clearPassword}
									class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
								Clear saved password
							</label>
						{/if}
					</div>

					<div>
						<label
							for="smtp-from-email"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							From Email Address <span class="text-red-500">*</span>
						</label>
						<input
							id="smtp-from-email"
							type="email"
							bind:value={fromEmail}
							placeholder="billing@yourdomain.com"
							required={enabled}
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div>
						<label
							for="smtp-from-name"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							From Display Name
						</label>
						<input
							id="smtp-from-name"
							type="text"
							bind:value={fromName}
							placeholder="ZenEngr Billing"
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
				</div>

				<div
					class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-t border-slate-100 pt-5"
				>
					<button
						type="button"
						disabled={testing}
						aria-busy={testing}
						onclick={sendTest}
						class="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 sm:py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60"
					>
						{#if testing}<Spinner class="h-3 w-3" />{/if}
						<Icon icon={sendOutline} class="h-3.5 w-3.5 text-slate-500" />
						Send Test Email
					</button>

					<button
						type="submit"
						disabled={saving}
						aria-busy={saving}
						class="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 sm:py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60"
					>
						{#if saving}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
						Save SMTP Configuration
					</button>
				</div>

				{#if testMsg}
					<div
						role="status"
						class="rounded-lg border border-emerald-200 bg-emerald-50 p-3.5 text-xs font-semibold text-emerald-800"
					>
						✓ {testMsg}
					</div>
				{/if}
				{#if testErr}
					<div
						role="alert"
						class="rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs font-semibold text-red-800"
					>
						{testErr}
					</div>
				{/if}
			</div>
		</section>
	</form>
</div>
