<script>
	import { invalidateAll } from '$app/navigation';
	import { untrack } from 'svelte';
	import { ApiError } from '$lib/api/client.js';
	import * as smtpApi from '$lib/api/smtp.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

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
			saveErr = 'Host and From email are required when SMTP is enabled.';
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
			saveMsg = 'Saved.';
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
			testErr = e instanceof ApiError ? e.message : 'Test failed.';
		} finally {
			testing = false;
		}
	}
</script>

<svelte:head><title>Email (SMTP) — ZenEngr</title></svelte:head>

<h1 class="text-2xl font-semibold text-slate-900">Email (SMTP)</h1>
<p class="mt-1 text-sm text-slate-500">
	Configure the SMTP server used to send emails from this tenant.
</p>

<section
	class="mt-6 max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="smtp-h"
>
	<h2 id="smtp-h" class="text-base font-semibold text-slate-900">SMTP settings</h2>
	{#if saveMsg}
		<p
			role="status"
			class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
		>
			{saveMsg}
		</p>
	{/if}
	{#if saveErr}
		<p
			role="alert"
			class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{saveErr}
		</p>
	{/if}
	<form
		class="mt-4 space-y-4"
		onsubmit={(e) => {
			e.preventDefault();
			saveSmtp();
		}}
	>
		<label class="inline-flex items-center gap-2 text-sm text-slate-700">
			<input
				type="checkbox"
				bind:checked={enabled}
				class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
			/>
			Send email via SMTP
		</label>
		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<label for="smtp-host" class="block text-sm font-medium text-slate-700">Host</label>
				<input
					id="smtp-host"
					type="text"
					bind:value={host}
					placeholder="smtp.example.com"
					required={enabled}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="smtp-port" class="block text-sm font-medium text-slate-700">Port</label>
				<input
					id="smtp-port"
					type="number"
					bind:value={port}
					min="1"
					max="65535"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="smtp-username" class="block text-sm font-medium text-slate-700">Username</label>
				<input
					id="smtp-username"
					type="text"
					bind:value={username}
					autocomplete="off"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="smtp-password" class="block text-sm font-medium text-slate-700">Password</label>
				<input
					id="smtp-password"
					type="password"
					bind:value={password}
					disabled={clearPassword}
					placeholder={initial.has_password ? '•••••• (unchanged)' : ''}
					autocomplete="new-password"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
				/>
				{#if hasPassword}
					<label class="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs text-slate-600">
						<input
							type="checkbox"
							bind:checked={clearPassword}
							class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
						/>
						Clear saved password
					</label>
					<p class="mt-1 text-xs text-slate-500">Leave blank to keep the current password.</p>
					{#if (username ?? '').trim() === ''}
						<p class="mt-1 text-xs text-amber-600">
							Username is empty — saving will also clear the saved password.
						</p>
					{/if}
				{:else}
					<p class="mt-1 text-xs text-slate-500">
						No password saved — fine for unauthenticated SMTP (e.g. Mailpit).
					</p>
				{/if}
			</div>
			<div>
				<label for="smtp-from-email" class="block text-sm font-medium text-slate-700"
					>From email</label
				>
				<input
					id="smtp-from-email"
					type="email"
					bind:value={fromEmail}
					placeholder="noreply@example.com"
					required={enabled}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="smtp-from-name" class="block text-sm font-medium text-slate-700"
					>From name</label
				>
				<input
					id="smtp-from-name"
					type="text"
					bind:value={fromName}
					placeholder="ZenEngr"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="smtp-mode" class="block text-sm font-medium text-slate-700">Security mode</label
				>
				<select
					id="smtp-mode"
					bind:value={mode}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				>
					<option value="none">None</option>
					<option value="starttls">STARTTLS</option>
					<option value="ssl">SSL</option>
				</select>
			</div>
		</div>
		<div class="flex flex-wrap items-center gap-3">
			<button
				type="submit"
				disabled={saving}
				aria-busy={saving}
				class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if saving}<Spinner class="h-4 w-4 text-white" />{/if}
				Save
			</button>
			<button
				type="button"
				disabled={testing}
				aria-busy={testing}
				onclick={sendTest}
				class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if testing}<Spinner class="h-3.5 w-3.5" />{/if}
				Send test email
			</button>
		</div>
	</form>
	{#if testMsg}
		<p
			role="status"
			class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
		>
			{testMsg}
		</p>
	{/if}
	{#if testErr}
		<p
			role="alert"
			class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{testErr}
		</p>
	{/if}
</section>
