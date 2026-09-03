<script>
	import * as accountApi from '$lib/api/account.js';
	import { ApiError, assetUrl } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import ScrollableTabs from '$lib/components/ScrollableTabs.svelte';
	import TimezoneSelect from '$lib/components/TimezoneSelect.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { formatAddress } from '$lib/utils/address.js';
	import Icon from '@iconify/svelte';
	import accountOutline from '@iconify-icons/mdi/account-outline';
	import officeBuilding from '@iconify-icons/mdi/office-building';
	import lockOutline from '@iconify-icons/mdi/lock-outline';
	import bellOutline from '@iconify-icons/mdi/bell-outline';
	import checkCircle from '@iconify-icons/mdi/check-circle';
	import alertCircleOutline from '@iconify-icons/mdi/alert-circle-outline';
	import upload from '@iconify-icons/mdi/upload';
	import trashCanOutline from '@iconify-icons/mdi/trash-can-outline';

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

	function getInitials(name) {
		if (!name) return 'U';
		return name
			.split(' ')
			.map((p) => p[0])
			.filter(Boolean)
			.slice(0, 2)
			.join('')
			.toUpperCase();
	}

	let avatarFileInput = $state(/** @type {HTMLInputElement|null} */ (null));
	let uploadingAvatar = $state(false);
	let avatarError = $state(/** @type {string|null} */ (null));
	let avatarSuccess = $state(/** @type {string|null} */ (null));
	let imageLoadFailed = $state(false);

	async function handleAvatarSelect(e) {
		const files = e.target?.files;
		if (!files || files.length === 0) return;
		const file = files[0];
		if (file.size > 5 * 1024 * 1024) {
			avatarError = 'Image must be smaller than 5MB.';
			return;
		}
		uploadingAvatar = true;
		avatarError = null;
		avatarSuccess = null;
		try {
			const res = await accountApi.uploadAvatar(fetch, token, file, { realm: 'client' });
			accountAvatar = res.avatar_url;
			imageLoadFailed = false;
			if (portalAuth.user) portalAuth.user.avatar_url = res.avatar_url;
			avatarSuccess = 'Profile picture updated successfully.';
			setTimeout(() => (avatarSuccess = null), 4000);
		} catch (err) {
			avatarError = err instanceof ApiError ? err.message : 'Upload failed. Please try again.';
		} finally {
			uploadingAvatar = false;
			if (avatarFileInput) avatarFileInput.value = '';
		}
	}

	async function removeAvatar() {
		if (uploadingAvatar) return;
		uploadingAvatar = true;
		avatarError = null;
		avatarSuccess = null;
		try {
			await accountApi.deleteAvatar(fetch, token, { realm: 'client' });
			accountAvatar = '';
			imageLoadFailed = false;
			if (portalAuth.user) portalAuth.user.avatar_url = null;
			avatarSuccess = 'Profile picture removed.';
			setTimeout(() => (avatarSuccess = null), 4000);
		} catch (err) {
			avatarError = err instanceof ApiError ? err.message : 'Failed to remove picture.';
		} finally {
			uploadingAvatar = false;
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
			<p class="text-xs text-slate-500">
				Manage your profile, credentials, and company preferences
			</p>
		</div>
	</div>

	<!-- Tab Navigation Modules -->
	<ScrollableTabs ariaLabel="Profile sections">
		{#each TABS as tab (tab.id)}
			{@const active = activeTab === tab.id}
			<button
				type="button"
				onclick={() => (activeTab = tab.id)}
				class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all {active
					? 'bg-indigo-600 text-white shadow-2xs'
					: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
			>
				<Icon icon={tab.icon} class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}" />
				<span>{tab.label}</span>
			</button>
		{/each}
	</ScrollableTabs>

	<!-- Module 1: Personal Profile -->
	{#if activeTab === 'profile'}
		<section class="max-w-3xl rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<h2 class="border-b border-slate-100 pb-4 text-sm font-bold text-slate-900">
				Personal Information
			</h2>

			{#if accountSuccess}
				<div
					role="status"
					class="mt-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800"
				>
					<Icon icon={checkCircle} class="h-4 w-4 shrink-0 text-emerald-600" />
					{accountSuccess}
				</div>
			{/if}
			{#if accountError}
				<div
					role="alert"
					class="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800"
				>
					<Icon icon={alertCircleOutline} class="h-4 w-4 shrink-0 text-red-600" />
					{accountError}
				</div>
			{/if}

			<!-- Profile Picture Management Card -->
			<div class="mt-5 rounded-xl border border-slate-200/90 bg-slate-50/60 p-4 sm:p-5">
				<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
					<div class="flex items-center gap-4">
						<div
							class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 text-lg font-bold text-white shadow-sm ring-2 ring-white"
						>
							{#if accountAvatar && !imageLoadFailed}
								<img
									src={assetUrl(accountAvatar)}
									alt=""
									class="h-full w-full object-cover"
									onerror={() => (imageLoadFailed = true)}
								/>
							{:else}
								{getInitials(accountFullName)}
							{/if}
						</div>
						<div>
							<h3 class="text-xs font-bold tracking-wide text-slate-700 uppercase">Profile Photo</h3>
							<p class="mt-0.5 text-xs text-slate-500">
								Upload a PNG, JPEG, WebP, or GIF (max 5MB).
							</p>
							{#if avatarSuccess}
								<p class="mt-1 text-xs font-semibold text-emerald-600">✓ {avatarSuccess}</p>
							{/if}
							{#if avatarError}
								<p class="mt-1 text-xs font-semibold text-red-600">✗ {avatarError}</p>
							{/if}
						</div>
					</div>

					<div class="flex flex-wrap items-center gap-2">
						<input
							type="file"
							accept="image/png,image/jpeg,image/webp,image/gif"
							bind:this={avatarFileInput}
							onchange={handleAvatarSelect}
							class="hidden"
							id="client-avatar-file-input"
						/>
						<button
							type="button"
							onclick={() => avatarFileInput?.click()}
							disabled={uploadingAvatar}
							class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 disabled:opacity-60"
						>
							{#if uploadingAvatar}
								<Spinner class="h-3.5 w-3.5 text-indigo-600" />
								Uploading...
							{:else}
								<Icon icon={upload} class="h-3.5 w-3.5 text-slate-500" />
								Upload New Picture
							{/if}
						</button>
						{#if accountAvatar}
							<button
								type="button"
								onclick={removeAvatar}
								disabled={uploadingAvatar}
								class="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 shadow-2xs transition-colors hover:bg-rose-100 disabled:opacity-60"
							>
								<Icon icon={trashCanOutline} class="h-3.5 w-3.5" />
								Remove
							</button>
						{/if}
					</div>
				</div>
			</div>

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

				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
							<p class="mt-1 text-[11px] font-medium text-amber-600">
								Pending confirmation: {pendingEmail}
							</p>
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

				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div>
						<label for="acc-tz" class="block font-semibold text-slate-700">Timezone</label>
						<div class="mt-1">
							<TimezoneSelect id="acc-tz" bind:value={accountTimezone} />
						</div>
					</div>

					<div>
						<label for="acc-lang" class="block font-semibold text-slate-700"
							>Preferred Language</label
						>
						<select
							id="acc-lang"
							bind:value={accountLanguage}
							class="mt-1 block w-full rounded-lg border-slate-300 py-2 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						>
							<option value="en">English (US)</option>
							<option value="es">Español</option>
							<option value="fr">Français</option>
							<option value="de">Deutsch</option>
						</select>
					</div>
				</div>

				<div class="flex justify-end pt-4">
					<button
						type="submit"
						disabled={savingAccount}
						class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 disabled:opacity-60"
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
		<section class="max-w-3xl rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
				<div>
					<h2 class="text-sm font-bold text-slate-900">Company Information</h2>
					<p class="mt-0.5 text-xs text-slate-500">
						Assigned company profile and billing representation
					</p>
				</div>
				<StatusBadge status={client.status} />
			</div>

			{#if companySuccess}
				<div
					role="status"
					class="mt-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800"
				>
					<Icon icon={checkCircle} class="h-4 w-4 shrink-0 text-emerald-600" />
					{companySuccess}
				</div>
			{/if}
			{#if companyError}
				<div
					role="alert"
					class="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800"
				>
					<Icon icon={alertCircleOutline} class="h-4 w-4 shrink-0 text-red-600" />
					{companyError}
				</div>
			{/if}

			<div class="mt-5 space-y-4 text-xs">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5">
						<span class="text-[10px] font-bold tracking-wider text-slate-400 uppercase"
							>Company Name</span
						>
						<p class="mt-1 text-sm font-bold text-slate-900">{client.name}</p>
					</div>
					<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5">
						<span class="text-[10px] font-bold tracking-wider text-slate-400 uppercase"
							>Tax ID / VAT</span
						>
						<p class="mt-1 text-sm font-bold text-slate-900">{client.tax_id || '—'}</p>
					</div>
				</div>

				<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5">
					<span class="text-[10px] font-bold tracking-wider text-slate-400 uppercase"
						>Billing Address</span
					>
					<p class="mt-1 text-xs whitespace-pre-wrap text-slate-700">
						{formatAddress(client.billing_address) || 'No billing address on file.'}
					</p>
				</div>

				<form
					class="space-y-4 border-t border-slate-100 pt-4"
					onsubmit={(e) => {
						e.preventDefault();
						saveCompanyContact();
					}}
				>
					<h3 class="text-xs font-bold text-slate-900">Company Contact Details</h3>
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
						<div>
							<label for="comp-email" class="block font-semibold text-slate-700"
								>Billing / General Email</label
							>
							<input
								id="comp-email"
								type="email"
								bind:value={companyEmail}
								class="mt-1 block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>
						<div>
							<label for="comp-phone" class="block font-semibold text-slate-700"
								>Company Phone</label
							>
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
							class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 disabled:opacity-60"
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
		<section class="max-w-3xl rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<h2 class="border-b border-slate-100 pb-4 text-sm font-bold text-slate-900">
				Security & Password
			</h2>

			{#if changeSuccess}
				<div
					role="status"
					class="mt-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800"
				>
					<Icon icon={checkCircle} class="h-4 w-4 shrink-0 text-emerald-600" />
					{changeSuccess}
				</div>
			{/if}
			{#if changeError}
				<div
					role="alert"
					class="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800"
				>
					<Icon icon={alertCircleOutline} class="h-4 w-4 shrink-0 text-red-600" />
					{changeError}
				</div>
			{/if}

			<form
				class="mt-5 max-w-md space-y-4 text-xs"
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
					<label for="conf-pwd" class="block font-semibold text-slate-700"
						>Confirm New Password</label
					>
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
						class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 disabled:opacity-60"
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
		<section class="max-w-3xl rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
				<div>
					<h2 class="text-sm font-bold text-slate-900">Notification Preferences</h2>
					<p class="mt-0.5 text-xs text-slate-500">
						Control which event alerts you receive via email and in-app bell
					</p>
				</div>
				{#if prefsSaved}
					<span class="flex items-center gap-1 text-xs font-semibold text-emerald-600">
						<Icon icon={checkCircle} class="h-4 w-4" />
						Saved
					</span>
				{/if}
			</div>

			{#if prefsError}
				<div
					role="alert"
					class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800"
				>
					{prefsError}
				</div>
			{/if}

			<div class="mt-6 space-y-6 text-xs">
				<!-- In-App Notifications -->
				<div>
					<h3 class="mb-3 font-bold text-slate-900">In-App Notifications</h3>
					<div class="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
						{#each inappPrefs as pref (pref.event_type)}
							<label
								class="flex cursor-pointer items-center justify-between gap-3 p-3 hover:bg-slate-50/50"
							>
								<span class="min-w-0 font-semibold text-slate-700"
									>{EVENT_LABELS[pref.event_type] || pref.event_type}</span
								>
								<input
									type="checkbox"
									checked={pref.enabled}
									disabled={savingPref === `inapp:${pref.event_type}`}
									onchange={(e) => togglePref('inapp', pref.event_type, e.currentTarget.checked)}
									class="h-4 w-4 shrink-0 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
							</label>
						{/each}
					</div>
				</div>

				<!-- Email Notifications -->
				<div>
					<h3 class="mb-3 font-bold text-slate-900">Email Alerts</h3>
					<div class="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
						{#each emailPrefs as pref (pref.event_type)}
							<label
								class="flex cursor-pointer items-center justify-between gap-3 p-3 hover:bg-slate-50/50"
							>
								<span class="min-w-0 font-semibold text-slate-700"
									>{EVENT_LABELS[pref.event_type] || pref.event_type}</span
								>
								<input
									type="checkbox"
									checked={pref.enabled}
									disabled={savingPref === `email:${pref.event_type}`}
									onchange={(e) => togglePref('email', pref.event_type, e.currentTarget.checked)}
									class="h-4 w-4 shrink-0 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
							</label>
						{/each}
					</div>
				</div>
			</div>
		</section>
	{/if}
</div>
