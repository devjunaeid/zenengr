<script>
	import { invalidateAll } from '$app/navigation';
	import { untrack } from 'svelte';
	import * as accountApi from '$lib/api/account.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDateTime, humanize } from '$lib/utils/format.js';

	// Layout guard guarantees these exist
	let { data } = $props();
	const token = /** @type {string} */ (auth.token);
	const initial = untrack(() => data.profile);
	const activity = untrack(() => data.activity);

	// ── Account profile form ────────────────────────────────────────────────

	let fullName = $state(initial.full_name ?? '');
	let email = $state(initial.email ?? '');
	let phone = $state(initial.phone ?? '');
	let timezone = $state(initial.timezone ?? '');
	let language = $state(initial.language ?? '');
	let avatarUrl = $state(initial.avatar_url ?? '');
	let saving = $state(false);
	/** @type {string|null} */
	let saveError = $state(null);
	/** @type {string|null} */
	let saveSuccess = $state(null);

	async function saveProfile() {
		if (saving) return;
		saving = true;
		saveError = null;
		saveSuccess = null;
		try {
			/** @type {Record<string, any>} */
			const body = {
				full_name: fullName.trim(),
				email: email.trim(),
				phone: phone.trim() || null,
				timezone: timezone.trim() || null,
				language: language.trim() || null,
				avatar_url: avatarUrl.trim() || null
			};
			const updated = await accountApi.updateProfile(fetch, token, body, { realm: 'admin' });
			fullName = updated.full_name;
			email = updated.email;
			phone = updated.phone ?? '';
			timezone = updated.timezone ?? '';
			language = updated.language ?? '';
			avatarUrl = updated.avatar_url ?? '';
			// Keep the header name in sync
			if (auth.user) auth.user.full_name = updated.full_name;
			await invalidateAll();
			saveSuccess = updated.pending_email
				? 'Profile updated. Check your inbox to confirm the new email.'
				: 'Profile updated.';
		} catch (e) {
			saveError = e instanceof ApiError ? e.message : 'Unable to save. Try again.';
		} finally {
			saving = false;
		}
	}

	// ── Change password ─────────────────────────────────────────────────────

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let changing = $state(false);
	/** @type {string|null} */
	let changeError = $state(null);
	/** @type {string|null} */
	let changeSuccess = $state(null);

	async function submitPassword() {
		if (changing) return;
		changeError = null;
		changeSuccess = null;
		if (newPassword.length < 8) {
			changeError = 'New password must be at least 8 characters.';
			return;
		}
		if (newPassword !== confirmPassword) {
			changeError = 'New password and confirmation do not match.';
			return;
		}
		changing = true;
		try {
			await accountApi.changePassword(
				fetch,
				token,
				{ current_password: currentPassword, new_password: newPassword },
				{ realm: 'admin' }
			);
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
			changeSuccess = 'Password updated.';
		} catch (e) {
			changeError = e instanceof ApiError ? e.message : 'Unable to change password. Try again.';
		} finally {
			changing = false;
		}
	}
</script>

<svelte:head><title>Profile — ZenEngr</title></svelte:head>

<h1 class="text-2xl font-semibold text-slate-900">Profile</h1>
<p class="mt-1 text-sm text-slate-500">Your account details, security, and activity.</p>

<div class="mt-6 space-y-6">
	<!-- Account profile -->
	<section
		class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="acct-h"
	>
		<h2 id="acct-h" class="text-base font-semibold text-slate-900">Account profile</h2>
		<p class="mt-1 text-sm text-slate-500">
			Update your name and contact details. Changing your email sends a verification email.
		</p>

		{#if initial.pending_email}
			<div
				role="status"
				class="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
			>
				Verification pending for {initial.pending_email}. Check your inbox to confirm.
			</div>
		{/if}
		{#if saveError}
			<div
				role="alert"
				class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{saveError}
			</div>
		{/if}
		{#if saveSuccess}
			<div
				role="status"
				class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
			>
				{saveSuccess}
			</div>
		{/if}

		<form
			class="mt-4 max-w-2xl space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				saveProfile();
			}}
		>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="p-full-name" class="block text-sm font-medium text-slate-700">Full name</label
					>
					<input
						id="p-full-name"
						type="text"
						bind:value={fullName}
						required
						autocomplete="name"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="p-email" class="block text-sm font-medium text-slate-700">Email</label>
					<input
						id="p-email"
						type="email"
						bind:value={email}
						required
						autocomplete="email"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-xs text-slate-500">
						Changing email sends a verification email before the address is active.
					</p>
				</div>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="p-phone" class="block text-sm font-medium text-slate-700">Phone</label>
					<input
						id="p-phone"
						type="tel"
						bind:value={phone}
						autocomplete="tel"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="p-timezone" class="block text-sm font-medium text-slate-700">Timezone</label>
					<input
						id="p-timezone"
						type="text"
						bind:value={timezone}
						placeholder="America/New_York"
						autocomplete="off"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-xs text-slate-500">IANA timezone, e.g. "America/New_York".</p>
				</div>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="p-language" class="block text-sm font-medium text-slate-700">Language</label>
					<input
						id="p-language"
						type="text"
						bind:value={language}
						placeholder="en"
						autocomplete="off"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-xs text-slate-500">Language code, e.g. "en".</p>
				</div>
				<div>
					<label for="p-avatar" class="block text-sm font-medium text-slate-700">Avatar URL</label>
					<input
						id="p-avatar"
						type="url"
						bind:value={avatarUrl}
						autocomplete="off"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
			<div>
				<button
					type="submit"
					disabled={saving}
					aria-busy={saving}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if saving}<Spinner class="h-4 w-4 text-white" />{/if}
					Save changes
				</button>
			</div>
		</form>
	</section>

	<!-- Change password -->
	<section class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby="pw-h">
		<h2 id="pw-h" class="text-base font-semibold text-slate-900">Change password</h2>
		<p class="mt-1 text-sm text-slate-500">
			Your tenant's password policy applies (minimum 8 characters).
		</p>

		{#if changeError}
			<div
				role="alert"
				class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{changeError}
			</div>
		{/if}
		{#if changeSuccess}
			<div
				role="status"
				class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
			>
				{changeSuccess}
			</div>
		{/if}

		<form
			class="mt-4 max-w-md space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				submitPassword();
			}}
		>
			<div>
				<label for="pw-current" class="block text-sm font-medium text-slate-700"
					>Current password</label
				>
				<input
					id="pw-current"
					type="password"
					bind:value={currentPassword}
					required
					autocomplete="current-password"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="pw-new" class="block text-sm font-medium text-slate-700">New password</label>
				<input
					id="pw-new"
					type="password"
					bind:value={newPassword}
					required
					minlength="8"
					autocomplete="new-password"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="pw-confirm" class="block text-sm font-medium text-slate-700"
					>Confirm new password</label
				>
				<input
					id="pw-confirm"
					type="password"
					bind:value={confirmPassword}
					required
					minlength="8"
					autocomplete="new-password"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<button
					type="submit"
					disabled={changing}
					aria-busy={changing}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if changing}<Spinner class="h-4 w-4 text-white" />{/if}
					Update password
				</button>
			</div>
		</form>
	</section>

	<!-- Activity history -->
	<section
		class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
		aria-labelledby="act-h"
	>
		<h2
			id="act-h"
			class="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
		>
			Activity history
		</h2>
		{#if activity.length === 0}
			<p class="px-6 py-4 text-sm text-slate-500">No activity recorded yet.</p>
		{:else}
			<div class="overflow-x-auto">
				<table class="min-w-full divide-y divide-slate-200">
					<thead class="bg-slate-50">
						<tr>
							<th
								scope="col"
								class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
								>Event</th
							>
							<th
								scope="col"
								class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
								>Description</th
							>
							<th
								scope="col"
								class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
								>Change</th
							>
							<th
								scope="col"
								class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
								>Date</th
							>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-200">
						{#each activity as entry (entry.id)}
							<tr class="hover:bg-slate-50">
								<td class="px-4 py-3 text-sm font-medium text-slate-800">
									{humanize(entry.event_type)}
								</td>
								<td class="px-4 py-3 text-sm text-slate-600">{entry.description || '—'}</td>
								<td class="px-4 py-3 text-sm text-slate-600">
									{#if entry.old_value || entry.new_value}
										<span class="font-mono text-xs">{entry.old_value ?? '—'}</span>
										<span class="mx-1 text-slate-400">→</span>
										<span class="font-mono text-xs">{entry.new_value ?? '—'}</span>
									{:else}
										—
									{/if}
								</td>
								<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600">
									{formatDateTime(entry.created_at)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
</div>
