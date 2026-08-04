<script>
	import * as accountApi from '$lib/api/account.js';
	import { ApiError } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { formatDateTime, humanize } from '$lib/utils/format.js';

	// Layout guard guarantees these exist
	const client = /** @type {import('$lib/api/portal.js').PortalClient} */ (portalAuth.client);
	const token = /** @type {string} */ (portalAuth.token);

	// Account (portal user) initial values from the session store
	// (store typedef covers login fields only; cast for extended profile fields)
	const sessionUser = /** @type {any} */ (portalAuth.user) ?? {};
	const accountInitial = {
		full_name: sessionUser.full_name ?? '',
		email: sessionUser.email ?? '',
		phone: sessionUser.phone ?? '',
		timezone: sessionUser.timezone ?? '',
		language: sessionUser.language ?? '',
		avatar_url: sessionUser.avatar_url ?? '',
		pending_email: sessionUser.pending_email ?? null
	};

	// Contact edit state
	let email = $state(client.email ?? '');
	let phone = $state(client.phone ?? '');
	let saving = $state(false);
	/** @type {string|null} */
	let saveError = $state(null);
	/** @type {string|null} */
	let saveSuccess = $state(null);

	async function saveContact() {
		if (saving) return;
		saving = true;
		saveError = null;
		saveSuccess = null;
		try {
			const fields = {};
			if (email !== (client.email ?? '')) fields.email = email;
			if (phone !== (client.phone ?? '')) fields.phone = phone;
			if (Object.keys(fields).length === 0) {
				saveSuccess = 'No changes to save.';
				saving = false;
				return;
			}
			await portalApi.updateProfile(fetch, /** @type {string} */ (portalAuth.token), fields);
			// Refresh client data in store
			const me = await portalApi.me(fetch, /** @type {string} */ (portalAuth.token));
			// Update local reference
			if (portalAuth.client) {
				portalAuth.client.email = me.client.email;
				portalAuth.client.phone = me.client.phone;
			}
			saveSuccess = 'Contact details updated.';
		} catch (e) {
			if (e instanceof ApiError) {
				saveError = e.message;
			} else {
				saveError = 'Unable to save. Try again.';
			}
		} finally {
			saving = false;
		}
	}

	/**
	 * Render billing address as readable lines.
	 * @param {Record<string,any>|null} addr
	 */
	function renderAddress(addr) {
		if (!addr) return '—';
		const parts = [];
		if (addr.line1) parts.push(addr.line1);
		if (addr.line2) parts.push(addr.line2);
		if (addr.city || addr.state || addr.postal_code) {
			parts.push([addr.city, addr.state, addr.postal_code].filter(Boolean).join(', '));
		}
		if (addr.country) parts.push(addr.country);
		return parts.length ? parts.join('\n') : '—';
	}

	// ── Account (portal user) profile ──────────────────────────────────────

	let accountFullName = $state(accountInitial.full_name);
	let accountEmail = $state(accountInitial.email);
	let accountPhone = $state(accountInitial.phone);
	let accountTimezone = $state(accountInitial.timezone);
	let accountLanguage = $state(accountInitial.language);
	let accountAvatar = $state(accountInitial.avatar_url);
	let pendingEmail = $state(accountInitial.pending_email);
	let savingAccount = $state(false);
	/** @type {string|null} */
	let accountError = $state(null);
	/** @type {string|null} */
	let accountSuccess = $state(null);

	async function saveAccount() {
		if (savingAccount) return;
		savingAccount = true;
		accountError = null;
		accountSuccess = null;
		try {
			/** @type {Record<string, any>} */
			const body = {
				full_name: accountFullName.trim(),
				email: accountEmail.trim(),
				phone: accountPhone.trim() || null,
				timezone: accountTimezone.trim() || null,
				language: accountLanguage.trim() || null,
				avatar_url: accountAvatar.trim() || null
			};
			const updated = await accountApi.updateProfile(fetch, token, body, { realm: 'client' });
			// Refresh session store user (getter exposes the reactive object)
			const me = await portalApi.me(fetch, token);
			if (portalAuth.user) {
				portalAuth.user.full_name = me.user.full_name;
				portalAuth.user.email = me.user.email;
			}
			accountFullName = updated.full_name;
			accountEmail = updated.email;
			accountPhone = updated.phone ?? '';
			accountTimezone = updated.timezone ?? '';
			accountLanguage = updated.language ?? '';
			accountAvatar = updated.avatar_url ?? '';
			pendingEmail = updated.pending_email ?? null;
			accountSuccess = pendingEmail
				? 'Account updated. Check your inbox to confirm the new email.'
				: 'Account updated.';
		} catch (e) {
			accountError = e instanceof ApiError ? e.message : 'Unable to save. Try again.';
		} finally {
			savingAccount = false;
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
				{ realm: 'client' }
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

	// ── Notification preferences ────────────────────────────────────────────

	const EVENT_TYPES = ['new_comment', 'invoice_issued', 'payment_received', 'milestone_completed'];

	/**
	 * @param {Array<{ event_type: string, enabled: boolean }>} loaded
	 */
	function buildPrefs(loaded) {
		return EVENT_TYPES.map((eventType) => {
			const found = loaded.find((p) => p.event_type === eventType);
			return { event_type: eventType, enabled: found ? found.enabled : false };
		});
	}

	let prefs = $state(buildPrefs([]));
	/** @type {string|null} */
	let savingPref = $state(null);
	/** @type {string|null} */
	let prefsError = $state(null);
	let prefsSaved = $state(false);

	accountApi
		.getNotificationPreferences(fetch, token, { realm: 'client' })
		.then((loaded) => {
			prefs = buildPrefs(loaded);
		})
		.catch((e) => {
			prefsError = e instanceof ApiError ? e.message : 'Unable to load preferences.';
		});

	/**
	 * @param {string} eventType
	 * @param {boolean} enabled
	 */
	async function togglePref(eventType, enabled) {
		if (savingPref) return;
		savingPref = eventType;
		prefsError = null;
		prefsSaved = false;
		try {
			const updated = await accountApi.updateNotificationPreferences(
				fetch,
				token,
				{ preferences: [{ event_type: eventType, enabled }] },
				{ realm: 'client' }
			);
			for (const p of updated) {
				const idx = prefs.findIndex((x) => x.event_type === p.event_type);
				if (idx >= 0) prefs[idx].enabled = p.enabled;
			}
			prefsSaved = true;
			setTimeout(() => (prefsSaved = false), 2000);
		} catch (e) {
			const idx = prefs.findIndex((x) => x.event_type === eventType);
			if (idx >= 0) prefs[idx].enabled = !enabled;
			prefsError = e instanceof ApiError ? e.message : 'Unable to save preference. Try again.';
		} finally {
			savingPref = null;
		}
	}

	// ── Activity history ────────────────────────────────────────────────────

	/** @type {Array<{ id: string, event_type: string, description: string, old_value: string|null, new_value: string|null, created_at: string }>} */
	let activity = $state([]);
	/** @type {string|null} */
	let activityError = $state(null);

	accountApi
		.getActivity(fetch, token, { realm: 'client' })
		.then((entries) => {
			activity = entries;
		})
		.catch((e) => {
			activityError = e instanceof ApiError ? e.message : 'Unable to load activity.';
		});
</script>

<svelte:head><title>Profile — Client Portal</title></svelte:head>

<div class="space-y-6">
	<h1 class="text-xl font-semibold text-slate-900">Profile</h1>

	<!-- Contact details card -->
	<div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
		<h2 class="text-base font-semibold text-slate-900">Contact details</h2>
		<p class="mt-1 text-sm text-slate-500">Update your email and phone number.</p>

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
			class="mt-4 space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				saveContact();
			}}
		>
			<div>
				<label for="email" class="block text-sm font-medium text-slate-700">Email</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					required
					autocomplete="email"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="phone" class="block text-sm font-medium text-slate-700">Phone</label>
				<input
					id="phone"
					type="tel"
					bind:value={phone}
					autocomplete="tel"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
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
	</div>

	<!-- Billing details card (read-only) -->
	<div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
		<h2 class="text-base font-semibold text-slate-900">Billing details</h2>
		<p class="mt-1 text-sm text-slate-500">
			Read-only. Contact your agency to change billing details.
		</p>

		<dl class="mt-4 space-y-3">
			<div>
				<dt class="text-sm font-medium text-slate-500">Client name</dt>
				<dd class="mt-0.5 text-sm text-slate-900">{client.name}</dd>
			</div>
			<div>
				<dt class="text-sm font-medium text-slate-500">Billing address</dt>
				<dd class="mt-0.5 text-sm whitespace-pre-line text-slate-900">
					{renderAddress(client.billing_address)}
				</dd>
			</div>
			<div>
				<dt class="text-sm font-medium text-slate-500">Tax ID</dt>
				<dd class="mt-0.5 text-sm text-slate-900">{client.tax_id ?? '—'}</dd>
			</div>
		</dl>

		<p class="mt-4 text-xs text-slate-400">
			Need to change billing info? Contact your service provider.
		</p>
	</div>

	<!-- Your account (portal user) -->
	<div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
		<h2 class="text-base font-semibold text-slate-900">Your account</h2>
		<p class="mt-1 text-sm text-slate-500">
			Your portal profile, security, and notification settings.
		</p>

		<!-- Account profile -->
		<h3 class="mt-6 text-sm font-semibold text-slate-900">Account profile</h3>
		<p class="mt-1 text-sm text-slate-500">
			Changing your email sends a verification email before the address is active.
		</p>

		{#if pendingEmail}
			<div
				role="status"
				class="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
			>
				Verification pending for {pendingEmail}. Check your inbox to confirm.
			</div>
		{/if}
		{#if accountError}
			<div
				role="alert"
				class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{accountError}
			</div>
		{/if}
		{#if accountSuccess}
			<div
				role="status"
				class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
			>
				{accountSuccess}
			</div>
		{/if}

		<form
			class="mt-4 max-w-2xl space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				saveAccount();
			}}
		>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="acct-full-name" class="block text-sm font-medium text-slate-700"
						>Full name</label
					>
					<input
						id="acct-full-name"
						type="text"
						bind:value={accountFullName}
						required
						autocomplete="name"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="acct-email" class="block text-sm font-medium text-slate-700">Email</label>
					<input
						id="acct-email"
						type="email"
						bind:value={accountEmail}
						required
						autocomplete="email"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="acct-phone" class="block text-sm font-medium text-slate-700">Phone</label>
					<input
						id="acct-phone"
						type="tel"
						bind:value={accountPhone}
						autocomplete="tel"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="acct-timezone" class="block text-sm font-medium text-slate-700"
						>Timezone</label
					>
					<input
						id="acct-timezone"
						type="text"
						bind:value={accountTimezone}
						placeholder="America/New_York"
						autocomplete="off"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-xs text-slate-500">IANA timezone, e.g. "America/New_York".</p>
				</div>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="acct-language" class="block text-sm font-medium text-slate-700"
						>Language</label
					>
					<input
						id="acct-language"
						type="text"
						bind:value={accountLanguage}
						placeholder="en"
						autocomplete="off"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-xs text-slate-500">Language code, e.g. "en".</p>
				</div>
				<div>
					<label for="acct-avatar" class="block text-sm font-medium text-slate-700"
						>Avatar URL</label
					>
					<input
						id="acct-avatar"
						type="url"
						bind:value={accountAvatar}
						autocomplete="off"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
			<div>
				<button
					type="submit"
					disabled={savingAccount}
					aria-busy={savingAccount}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if savingAccount}<Spinner class="h-4 w-4 text-white" />{/if}
					Save changes
				</button>
			</div>
		</form>

		<!-- Change password -->
		<h3 class="mt-8 text-sm font-semibold text-slate-900">Change password</h3>
		<p class="mt-1 text-sm text-slate-500">Password policy: minimum 8 characters.</p>

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
				<label for="c-pw-current" class="block text-sm font-medium text-slate-700"
					>Current password</label
				>
				<input
					id="c-pw-current"
					type="password"
					bind:value={currentPassword}
					required
					autocomplete="current-password"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="c-pw-new" class="block text-sm font-medium text-slate-700">New password</label>
				<input
					id="c-pw-new"
					type="password"
					bind:value={newPassword}
					required
					minlength="8"
					autocomplete="new-password"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="c-pw-confirm" class="block text-sm font-medium text-slate-700"
					>Confirm new password</label
				>
				<input
					id="c-pw-confirm"
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

		<!-- Notification preferences -->
		<h3 class="mt-8 text-sm font-semibold text-slate-900">Notification preferences</h3>
		<p class="mt-1 text-sm text-slate-500">
			Choose which email notifications you receive. Saves immediately.
		</p>

		{#if prefsError}
			<div
				role="alert"
				class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{prefsError}
			</div>
		{/if}
		{#if prefsSaved}
			<div
				role="status"
				class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
			>
				Saved
			</div>
		{/if}

		<ul class="mt-4 max-w-md divide-y divide-slate-200">
			{#each prefs as pref (pref.event_type)}
				<li class="flex items-center justify-between py-3">
					<div>
						<p class="text-sm font-medium text-slate-800">{humanize(pref.event_type)}</p>
						<p class="text-xs text-slate-500">{pref.event_type}</p>
					</div>
					<label class="inline-flex items-center gap-2 text-sm text-slate-700">
						<input
							type="checkbox"
							checked={pref.enabled}
							disabled={savingPref !== null}
							onchange={(e) => togglePref(pref.event_type, e.currentTarget.checked)}
							class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
						/>
						{pref.enabled ? 'On' : 'Off'}
					</label>
				</li>
			{/each}
		</ul>

		<!-- Activity history -->
		<h3 class="mt-8 text-sm font-semibold text-slate-900">Activity history</h3>
		{#if activityError}
			<div
				role="alert"
				class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{activityError}
			</div>
		{:else if activity.length === 0}
			<p class="mt-3 text-sm text-slate-500">No activity recorded yet.</p>
		{:else}
			<div class="mt-3 overflow-x-auto rounded-lg border border-slate-200">
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
	</div>
</div>
