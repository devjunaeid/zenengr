<script>
	import * as accountApi from '$lib/api/account.js';
	import { ApiError } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import TimezoneSelect from '$lib/components/TimezoneSelect.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { formatAddress } from '$lib/utils/address.js';
	import { formatDateTime, humanize } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import accountOutline from '@iconify-icons/mdi/account-outline';
	import officeBuilding from '@iconify-icons/mdi/office-building';
	import lockOutline from '@iconify-icons/mdi/lock-outline';
	import bellOutline from '@iconify-icons/mdi/bell-outline';
	import checkCircle from '@iconify-icons/mdi/check-circle';
	import alertCircleOutline from '@iconify-icons/mdi/alert-circle-outline';

	// Layout guard guarantees these exist
	const client = /** @type {import('$lib/api/portal.js').PortalClient} */ (portalAuth.client);
	const token = /** @type {string} */ (portalAuth.token);

	let activeTab = $state('profile');

	const sessionUser = /** @type {any} */ (portalAuth.user) ?? {};
	const accountInitial = {
		full_name: sessionUser.full_name ?? '',
		email: sessionUser.email ?? '',
		phone: sessionUser.phone ?? '',
		timezone: sessionUser.timezone ?? 'UTC',
		language: sessionUser.language ?? 'en',
		avatar_url: sessionUser.avatar_url ?? '',
		pending_email: sessionUser.pending_email ?? null
	};

	// ── Company Contact edit state ──────────────────────────────────────────
	let companyEmail = $state(client.email ?? '');
	let companyPhone = $state(client.phone ?? '');
	let savingCompany = $state(false);
	let companyError = $state(/** @type {string|null} */ (null));
	let companySuccess = $state(/** @type {string|null} */ (null));

	async function saveCompanyContact() {
		if (savingCompany) return;
		savingCompany = true;
		companyError = null;
		companySuccess = null;
		try {
			const fields = {};
			if (companyEmail !== (client.email ?? '')) fields.email = companyEmail;
			if (companyPhone !== (client.phone ?? '')) fields.phone = companyPhone;
			if (Object.keys(fields).length === 0) {
				companySuccess = 'No changes to save.';
				savingCompany = false;
				return;
			}
			await portalApi.updateProfile(fetch, token, fields);
			const me = await portalApi.me(fetch, token);
			if (portalAuth.client) {
				portalAuth.client.email = me.client.email;
				portalAuth.client.phone = me.client.phone;
			}
			companySuccess = 'Company contact details updated.';
		} catch (e) {
			companyError = e instanceof ApiError ? e.message : 'Unable to save. Try again.';
		} finally {
			savingCompany = false;
		}
	}

	// ── Personal Account Profile ────────────────────────────────────────────
	let accountFullName = $state(accountInitial.full_name);
	let accountEmail = $state(accountInitial.email);
	let accountPhone = $state(accountInitial.phone);
	let accountTimezone = $state(accountInitial.timezone);
	let accountLanguage = $state(accountInitial.language);
	let accountAvatar = $state(accountInitial.avatar_url);
	let pendingEmail = $state(accountInitial.pending_email);
	let savingAccount = $state(false);
	let accountError = $state(/** @type {string|null} */ (null));
	let accountSuccess = $state(/** @type {string|null} */ (null));

	async function saveAccount() {
		if (savingAccount) return;
		savingAccount = true;
		accountError = null;
		accountSuccess = null;
		try {
			const body = {
				full_name: accountFullName.trim(),
				email: accountEmail.trim(),
				phone: accountPhone.trim() || null,
				timezone: accountTimezone.trim() || null,
				language: accountLanguage.trim() || null,
				avatar_url: accountAvatar.trim() || null
			};
			const updated = await accountApi.updateProfile(fetch, token, body, { realm: 'client' });
			const me = await portalApi.me(fetch, token);
			if (portalAuth.user) {
				portalAuth.user.full_name = me.full_name;
				portalAuth.user.email = me.email;
			}
			accountFullName = updated.full_name;
			accountEmail = updated.email;
			accountPhone = updated.phone ?? '';
			accountTimezone = updated.timezone ?? 'UTC';
			accountLanguage = updated.language ?? 'en';
			accountAvatar = updated.avatar_url ?? '';
			pendingEmail = updated.pending_email ?? null;
			accountSuccess = pendingEmail
				? 'Account updated. Check your inbox to confirm the new email.'
				: 'Account profile updated successfully.';
		} catch (e) {
			accountError = e instanceof ApiError ? e.message : 'Unable to save. Try again.';
		} finally {
			savingAccount = false;
		}
	}

	// ── Change Password ─────────────────────────────────────────────────────
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let changing = $state(false);
	let changeError = $state(/** @type {string|null} */ (null));
	let changeSuccess = $state(/** @type {string|null} */ (null));

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
			changeSuccess = 'Password updated successfully.';
		} catch (e) {
			changeError = e instanceof ApiError ? e.message : 'Unable to change password. Try again.';
		} finally {
			changing = false;
		}
	}

	// ── Notification Preferences ────────────────────────────────────────────
	const EVENT_TYPES = [
		'new_comment',
		'invoice_issued',
		'payment_received',
		'refund_recorded',
		'advance_applied',
		'milestone_completed',
		'project_created'
	];

	const EVENT_LABELS = {
		new_comment: 'New comment',
		invoice_issued: 'Invoice issued',
		payment_received: 'Payment received',
		refund_recorded: 'Refund recorded',
		advance_applied: 'Advance applied',
		milestone_completed: 'Milestone completed',
		project_created: 'Project created'
	};

	function buildPrefs(loaded) {
		return EVENT_TYPES.map((eventType) => {
			const found = loaded.find((p) => p.event_type === eventType);
			return { event_type: eventType, enabled: found ? found.enabled : false };
		});
	}

	let emailPrefs = $state(buildPrefs([]));
	let inappPrefs = $state(buildPrefs([]));
	let savingPref = $state(/** @type {string|null} */ (null));
	let prefsError = $state(/** @type {string|null} */ (null));
	let prefsSaved = $state(false);

	Promise.all([
		accountApi.getNotificationPreferences(fetch, token, { realm: 'client' }),
		accountApi.getNotificationPreferences(fetch, token, { realm: 'client', channel: 'inapp' })
	])
		.then(([email, inapp]) => {
			emailPrefs = buildPrefs(email);
			inappPrefs = buildPrefs(inapp);
		})
		.catch((e) => {
			prefsError = e instanceof ApiError ? e.message : 'Unable to load preferences.';
		});

	async function togglePref(channel, eventType, enabled) {
		if (savingPref) return;
		savingPref = `${channel}:${eventType}`;
		prefsError = null;
		prefsSaved = false;
		const arr = channel === 'inapp' ? inappPrefs : emailPrefs;
		try {
			const updated = await accountApi.updateNotificationPreferences(
				fetch,
				token,
				{ channel, preferences: [{ event_type: eventType, enabled }] },
				{ realm: 'client' }
			);
			for (const p of updated) {
				const idx = arr.findIndex((x) => x.event_type === p.event_type);
				if (idx >= 0) arr[idx].enabled = p.enabled;
			}
			prefsSaved = true;
			setTimeout(() => (prefsSaved = false), 2000);
		} catch (e) {
			const idx = arr.findIndex((x) => x.event_type === eventType);
			if (idx >= 0) arr[idx].enabled = !enabled;
			prefsError = e instanceof ApiError ? e.message : 'Unable to save preference.';
		} finally {
			savingPref = null;
		}
	}

	const TABS = [
		{ id: 'profile', label: 'Personal Profile', icon: accountOutline },
		{ id: 'company', label: 'Company Details', icon: officeBuilding },
		{ id: 'security', label: 'Security & Password', icon: lockOutline },
		{ id: 'notifications', label: 'Notifications', icon: bellOutline }
	];
</script>

<svelte:head><title>Account Settings — Client Portal</title></svelte:head>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-xl font-bold text-slate-900">Account & Profile Settings</h1>
			<p class="text-xs text-slate-500">Manage your profile, credentials, and company preferences</p>
		</div>
	</div>

	<!-- Tab Navigation Modules -->
	<div class="flex flex-wrap gap-1.5 rounded-xl border border-slate-200 bg-white p-1.5 shadow-2xs">
		{#each TABS as tab (tab.id)}
			{@const active = activeTab === tab.id}
			<button
				type="button"
				onclick={() => (activeTab = tab.id)}
				class="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition-all {active
					? 'bg-indigo-600 text-white shadow-2xs'
					: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
			>
				<Icon icon={tab.icon} class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}" />
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Module 1: Personal Profile -->
	{#if activeTab === 'profile'}
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs max-w-3xl">
			<h2 class="text-sm font-bold text-slate-900 pb-4 border-b border-slate-100">Personal Information</h2>

			{#if accountSuccess}
				<div role="status" class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 flex items-center gap-2">
					<Icon icon={checkCircle} class="h-4 w-4 text-emerald-600 shrink-0" />
					{accountSuccess}
				</div>
			{/if}
			{#if accountError}
				<div role="alert" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800 flex items-center gap-2">
					<Icon icon={alertCircleOutline} class="h-4 w-4 text-red-600 shrink-0" />
					{accountError}
				</div>
			{/if}

			<form
				class="mt-5 space-y-4 text-xs"
				onsubmit={(e) => {
					e.preventDefault();
					saveAccount();
				}}
			>
				<div>
					<label for="acc-name" class="block font-semibold text-slate-700">Full Name</label>
					<input
						id="acc-name"
						type="text"
						bind:value={accountFullName}
						required
						class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
					<div>
						<label for="acc-email" class="block font-semibold text-slate-700">Email Address</label>
						<input
							id="acc-email"
							type="email"
							bind:value={accountEmail}
							required
							class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
						{#if pendingEmail}
							<p class="mt-1 text-[11px] text-amber-600 font-medium">Pending confirmation: {pendingEmail}</p>
						{/if}
					</div>

					<div>
						<label for="acc-phone" class="block font-semibold text-slate-700">Phone Number</label>
						<input
							id="acc-phone"
							type="tel"
							bind:value={accountPhone}
							placeholder="+1..."
							class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
				</div>

				<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
					<div>
						<label for="acc-tz" class="block font-semibold text-slate-700">Timezone</label>
						<div class="mt-1">
							<TimezoneSelect id="acc-tz" bind:value={accountTimezone} />
						</div>
					</div>

					<div>
						<label for="acc-lang" class="block font-semibold text-slate-700">Preferred Language</label>
						<select
							id="acc-lang"
							bind:value={accountLanguage}
							class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 py-2"
						>
							<option value="en">English (US)</option>
							<option value="es">Español</option>
							<option value="fr">Français</option>
							<option value="de">Deutsch</option>
						</select>
					</div>
				</div>

				<div class="pt-4 flex justify-end">
					<button
						type="submit"
						disabled={savingAccount}
						class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 transition-colors disabled:opacity-60"
					>
						{#if savingAccount}
							<Spinner class="h-4 w-4 text-white" />
						{/if}
						Save Profile
					</button>
				</div>
			</form>
		</section>

	<!-- Module 2: Company Details -->
	{:else if activeTab === 'company'}
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs max-w-3xl">
			<div class="flex items-center justify-between pb-4 border-b border-slate-100">
				<div>
					<h2 class="text-sm font-bold text-slate-900">Company Information</h2>
					<p class="text-xs text-slate-500 mt-0.5">Assigned company profile and billing representation</p>
				</div>
				<StatusBadge status={client.status} />
			</div>

			{#if companySuccess}
				<div role="status" class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 flex items-center gap-2">
					<Icon icon={checkCircle} class="h-4 w-4 text-emerald-600 shrink-0" />
					{companySuccess}
				</div>
			{/if}
			{#if companyError}
				<div role="alert" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800 flex items-center gap-2">
					<Icon icon={alertCircleOutline} class="h-4 w-4 text-red-600 shrink-0" />
					{companyError}
				</div>
			{/if}

			<div class="mt-5 space-y-4 text-xs">
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
					<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5">
						<span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Company Name</span>
						<p class="mt-1 text-sm font-bold text-slate-900">{client.name}</p>
					</div>
					<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5">
						<span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Tax ID / VAT</span>
						<p class="mt-1 text-sm font-bold text-slate-900">{client.tax_id || '—'}</p>
					</div>
				</div>

				<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5">
					<span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Billing Address</span>
					<p class="mt-1 text-xs text-slate-700 whitespace-pre-wrap">{formatAddress(client.billing_address) || 'No billing address on file.'}</p>
				</div>

				<form
					class="pt-4 border-t border-slate-100 space-y-4"
					onsubmit={(e) => {
						e.preventDefault();
						saveCompanyContact();
					}}
				>
					<h3 class="font-bold text-slate-900 text-xs">Company Contact Details</h3>
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						<div>
							<label for="comp-email" class="block font-semibold text-slate-700">Billing / General Email</label>
							<input
								id="comp-email"
								type="email"
								bind:value={companyEmail}
								class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>
						<div>
							<label for="comp-phone" class="block font-semibold text-slate-700">Company Phone</label>
							<input
								id="comp-phone"
								type="tel"
								bind:value={companyPhone}
								class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>
					</div>

					<div class="flex justify-end pt-2">
						<button
							type="submit"
							disabled={savingCompany}
							class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 transition-colors disabled:opacity-60"
						>
							{#if savingCompany}
								<Spinner class="h-4 w-4 text-white" />
							{/if}
							Update Company Contact
						</button>
					</div>
				</form>
			</div>
		</section>

	<!-- Module 3: Security & Password -->
	{:else if activeTab === 'security'}
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs max-w-3xl">
			<h2 class="text-sm font-bold text-slate-900 pb-4 border-b border-slate-100">Security & Password</h2>

			{#if changeSuccess}
				<div role="status" class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 flex items-center gap-2">
					<Icon icon={checkCircle} class="h-4 w-4 text-emerald-600 shrink-0" />
					{changeSuccess}
				</div>
			{/if}
			{#if changeError}
				<div role="alert" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800 flex items-center gap-2">
					<Icon icon={alertCircleOutline} class="h-4 w-4 text-red-600 shrink-0" />
					{changeError}
				</div>
			{/if}

			<form
				class="mt-5 space-y-4 text-xs max-w-md"
				onsubmit={(e) => {
					e.preventDefault();
					submitPassword();
				}}
			>
				<div>
					<label for="cur-pwd" class="block font-semibold text-slate-700">Current Password</label>
					<input
						id="cur-pwd"
						type="password"
						bind:value={currentPassword}
						required
						class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div>
					<label for="new-pwd" class="block font-semibold text-slate-700">New Password</label>
					<input
						id="new-pwd"
						type="password"
						bind:value={newPassword}
						required
						minlength="8"
						class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
					<p class="mt-1 text-[11px] text-slate-400">Must be at least 8 characters long</p>
				</div>

				<div>
					<label for="conf-pwd" class="block font-semibold text-slate-700">Confirm New Password</label>
					<input
						id="conf-pwd"
						type="password"
						bind:value={confirmPassword}
						required
						minlength="8"
						class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div class="pt-2">
					<button
						type="submit"
						disabled={changing}
						class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 transition-colors disabled:opacity-60"
					>
						{#if changing}
							<Spinner class="h-4 w-4 text-white" />
						{/if}
						Change Password
					</button>
				</div>
			</form>
		</section>

	<!-- Module 4: Notification Preferences -->
	{:else if activeTab === 'notifications'}
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs max-w-3xl">
			<div class="flex items-center justify-between pb-4 border-b border-slate-100">
				<div>
					<h2 class="text-sm font-bold text-slate-900">Notification Preferences</h2>
					<p class="text-xs text-slate-500 mt-0.5">Control which event alerts you receive via email and in-app bell</p>
				</div>
				{#if prefsSaved}
					<span class="text-xs font-semibold text-emerald-600 flex items-center gap-1">
						<Icon icon={checkCircle} class="h-4 w-4" />
						Saved
					</span>
				{/if}
			</div>

			{#if prefsError}
				<div role="alert" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
					{prefsError}
				</div>
			{/if}

			<div class="mt-6 space-y-6 text-xs">
				<!-- In-App Notifications -->
				<div>
					<h3 class="font-bold text-slate-900 mb-3">In-App Notifications</h3>
					<div class="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
						{#each inappPrefs as pref (pref.event_type)}
							<label class="flex items-center justify-between p-3 hover:bg-slate-50/50 cursor-pointer">
								<span class="font-semibold text-slate-700">{EVENT_LABELS[pref.event_type] || pref.event_type}</span>
								<input
									type="checkbox"
									checked={pref.enabled}
									disabled={savingPref === `inapp:${pref.event_type}`}
									onchange={(e) => togglePref('inapp', pref.event_type, e.currentTarget.checked)}
									class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
							</label>
						{/each}
					</div>
				</div>

				<!-- Email Notifications -->
				<div>
					<h3 class="font-bold text-slate-900 mb-3">Email Alerts</h3>
					<div class="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
						{#each emailPrefs as pref (pref.event_type)}
							<label class="flex items-center justify-between p-3 hover:bg-slate-50/50 cursor-pointer">
								<span class="font-semibold text-slate-700">{EVENT_LABELS[pref.event_type] || pref.event_type}</span>
								<input
									type="checkbox"
									checked={pref.enabled}
									disabled={savingPref === `email:${pref.event_type}`}
									onchange={(e) => togglePref('email', pref.event_type, e.currentTarget.checked)}
									class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
							</label>
						{/each}
					</div>
				</div>
			</div>
		</section>
	{/if}
</div>
