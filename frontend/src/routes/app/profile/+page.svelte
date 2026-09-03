<script>
	import { invalidateAll } from '$app/navigation';
	import { untrack } from 'svelte';
	import * as accountApi from '$lib/api/account.js';
	import { ApiError, assetUrl } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import ScrollableTabs from '$lib/components/ScrollableTabs.svelte';
	import TimezoneSelect from '$lib/components/TimezoneSelect.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import accountCircle from '@iconify-icons/mdi/account-circle';
	import lockOutline from '@iconify-icons/mdi/lock-outline';
	import shieldCheck from '@iconify-icons/mdi/shield-check';
	import camera from '@iconify-icons/mdi/camera';
	import upload from '@iconify-icons/mdi/upload';
	import trashCanOutline from '@iconify-icons/mdi/trash-can-outline';

	let { data } = $props();
	const token = auth.token;
	const initial = untrack(() => data.profile);

	let activeSection = $state('details'); // 'details' | 'security'

	let fullName = $state(initial.full_name ?? '');
	let email = $state(initial.email ?? '');
	let phone = $state(initial.phone ?? '');
	let timezone = $state(initial.timezone ?? 'UTC');
	let language = $state(initial.language ?? 'en');
	let avatarUrl = $state(initial.avatar_url ?? '');
	let saving = $state(false);
	let saveError = $state(null);
	let saveSuccess = $state(null);

	async function saveProfile() {
		if (saving) return;
		saving = true;
		saveError = null;
		saveSuccess = null;
		try {
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
			timezone = updated.timezone ?? 'UTC';
			language = updated.language ?? 'en';
			avatarUrl = updated.avatar_url ?? '';
			if (auth.user) auth.user.full_name = updated.full_name;
			await invalidateAll();
			saveSuccess = updated.pending_email
				? 'Profile updated. Please check your inbox to verify your new email address.'
				: 'Your profile details have been successfully saved.';
			setTimeout(() => (saveSuccess = null), 4000);
		} catch (e) {
			saveError = e instanceof ApiError ? e.message : 'Unable to save profile. Please try again.';
		} finally {
			saving = false;
		}
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
			const res = await accountApi.uploadAvatar(fetch, token, file, { realm: 'admin' });
			avatarUrl = res.avatar_url;
			imageLoadFailed = false;
			if (auth.user) auth.user.avatar_url = res.avatar_url;
			await invalidateAll();
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
			await accountApi.deleteAvatar(fetch, token, { realm: 'admin' });
			avatarUrl = '';
			imageLoadFailed = false;
			if (auth.user) auth.user.avatar_url = null;
			await invalidateAll();
			avatarSuccess = 'Profile picture removed.';
			setTimeout(() => (avatarSuccess = null), 4000);
		} catch (err) {
			avatarError = err instanceof ApiError ? err.message : 'Failed to remove picture.';
		} finally {
			uploadingAvatar = false;
		}
	}

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let changing = $state(false);
	let changeError = $state(null);
	let changeSuccess = $state(null);

	async function submitPassword() {
		if (changing) return;
		changeError = null;
		changeSuccess = null;
		if (newPassword.length < 8) {
			changeError = 'New password must be at least 8 characters long.';
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
			changeSuccess = 'Password updated successfully.';
			setTimeout(() => (changeSuccess = null), 4000);
		} catch (e) {
			changeError =
				e instanceof ApiError
					? e.message
					: 'Unable to change password. Verify your current password.';
		} finally {
			changing = false;
		}
	}

	function getInitials(name) {
		if (!name) return 'U';
		return name
			.split(' ')
			.map((n) => n[0])
			.slice(0, 2)
			.join('')
			.toUpperCase();
	}
</script>

<svelte:head><title>My Account &amp; Profile — ZenEngr</title></svelte:head>

<div class="mx-auto w-full max-w-5xl space-y-6">
	<!-- Top Profile Summary Banner -->
	<section class="overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-2xs">
		<div class="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex items-center gap-4">
				<!-- Avatar / Initials with quick upload trigger -->
				<div class="relative group">
					<div
						class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 text-xl font-bold text-white shadow-sm ring-4 ring-slate-50"
					>
						{#if avatarUrl && !imageLoadFailed}
							<img
								src={assetUrl(avatarUrl)}
								alt=""
								class="h-full w-full object-cover"
								onerror={() => (imageLoadFailed = true)}
							/>
						{:else}
							{getInitials(fullName)}
						{/if}
					</div>
					<button
						type="button"
						onclick={() => avatarFileInput?.click()}
						disabled={uploadingAvatar}
						aria-label="Change profile picture"
						title="Change profile picture"
						class="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:text-indigo-600 focus-visible:ring-2 focus-visible:ring-indigo-500"
					>
						{#if uploadingAvatar}
							<Spinner class="h-3 w-3 text-indigo-600" />
						{:else}
							<Icon icon={camera} class="h-3.5 w-3.5" />
						{/if}
					</button>
				</div>

				<!-- Name & Badges -->
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<h1 class="text-xl font-bold text-slate-900">{fullName || 'User Profile'}</h1>
						<span
							class="rounded-md bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700 capitalize"
						>
							{data.user?.role ?? 'Team Member'}
						</span>
						<span
							class="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-600"
						>
							<span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span> Active
						</span>
					</div>
					<p class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
						<span>{email}</span>
						<span>•</span>
						<span>Member since {formatDate(data.profile?.created_at)}</span>
					</p>
				</div>
			</div>
		</div>

		<!-- Segmented Section Tabs -->
		<div class="mt-6 border-t border-slate-100 pt-4">
			<ScrollableTabs ariaLabel="Profile navigation">
				<button
					type="button"
					onclick={() => (activeSection = 'details')}
					class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all {activeSection ===
					'details'
						? 'bg-indigo-600 text-white shadow-2xs'
						: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
				>
					<Icon icon={accountCircle} class="h-4 w-4 shrink-0 {activeSection === 'details' ? 'text-white' : 'text-slate-400'}" />
					<span>Account Details</span>
				</button>
				<button
					type="button"
					onclick={() => (activeSection = 'security')}
					class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all {activeSection ===
					'security'
						? 'bg-indigo-600 text-white shadow-2xs'
						: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
				>
					<Icon icon={lockOutline} class="h-4 w-4 shrink-0 {activeSection === 'security' ? 'text-white' : 'text-slate-400'}" />
					<span>Password &amp; Security</span>
				</button>
			</ScrollableTabs>
		</div>
	</section>

	{#if activeSection === 'details'}
		<!-- Account Profile Details Form -->
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
					>
						<Icon icon={accountCircle} class="h-4 w-4" />
					</div>
					<div>
						<h2 class="text-sm font-bold text-slate-900">Personal Information</h2>
						<p class="text-xs text-slate-500">
							Update your name, contact details, and local timezone.
						</p>
					</div>
				</div>
			</div>

			<div class="p-6">
				{#if initial.pending_email}
					<div
						role="status"
						class="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-800"
					>
						⏳ Email change pending verification for <strong class="font-semibold"
							>{initial.pending_email}</strong
						>. Check your inbox to confirm.
					</div>
				{/if}
				{#if saveSuccess}
					<div
						role="status"
						class="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 p-3.5 text-xs font-semibold text-emerald-800"
					>
						✓ {saveSuccess}
					</div>
				{/if}
				{#if saveError}
					<div
						role="alert"
						class="mb-5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs font-semibold text-red-800"
					>
						{saveError}
					</div>
				{/if}

				<!-- Profile Picture Management Card -->
				<div class="mb-6 rounded-xl border border-slate-200/90 bg-slate-50/60 p-4 sm:p-5">
					<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
						<div class="flex items-center gap-4">
							<div
								class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 text-lg font-bold text-white shadow-sm ring-2 ring-white"
							>
								{#if avatarUrl && !imageLoadFailed}
									<img
										src={assetUrl(avatarUrl)}
										alt=""
										class="h-full w-full object-cover"
										onerror={() => (imageLoadFailed = true)}
									/>
								{:else}
									{getInitials(fullName)}
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
								id="avatar-file-input"
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
							{#if avatarUrl}
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
					class="space-y-5"
					onsubmit={(e) => {
						e.preventDefault();
						saveProfile();
					}}
				>
					<div class="grid gap-5 sm:grid-cols-2">
						<div>
							<label
								for="p-full-name"
								class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
							>
								Full Name <span class="text-red-500">*</span>
							</label>
							<input
								id="p-full-name"
								type="text"
								bind:value={fullName}
								required
								autocomplete="name"
								class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>

						<div>
							<label
								for="p-email"
								class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
							>
								Email Address <span class="text-red-500">*</span>
							</label>
							<input
								id="p-email"
								type="email"
								bind:value={email}
								required
								autocomplete="email"
								class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>

						<div>
							<label
								for="p-phone"
								class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
							>
								Phone Number
							</label>
							<input
								id="p-phone"
								type="tel"
								bind:value={phone}
								autocomplete="tel"
								placeholder="+1 (555) 000-0000"
								class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>

						<div>
							<label
								for="p-timezone"
								class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
							>
								Personal Timezone
							</label>
							<div class="mt-1.5">
								<TimezoneSelect id="p-timezone" bind:value={timezone} />
							</div>
						</div>

						<div>
							<label
								for="p-language"
								class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
							>
								Language Code
							</label>
							<input
								id="p-language"
								type="text"
								bind:value={language}
								placeholder="en"
								class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs uppercase shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>
					</div>

					<div class="flex justify-end border-t border-slate-100 pt-5">
						<button
							type="submit"
							disabled={saving}
							aria-busy={saving}
							class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60"
						>
							{#if saving}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
							Save Profile Changes
						</button>
					</div>
				</form>
			</div>
		</section>
	{:else if activeSection === 'security'}
		<!-- Change Password & Security Card -->
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
					>
						<Icon icon={shieldCheck} class="h-4 w-4" />
					</div>
					<div>
						<h2 class="text-sm font-bold text-slate-900">Password &amp; Authentication</h2>
						<p class="text-xs text-slate-500">
							Update your login password. Minimum 8 characters required.
						</p>
					</div>
				</div>
			</div>

			<div class="p-6">
				{#if changeSuccess}
					<div
						role="status"
						class="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 p-3.5 text-xs font-semibold text-emerald-800"
					>
						✓ {changeSuccess}
					</div>
				{/if}
				{#if changeError}
					<div
						role="alert"
						class="mb-5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs font-semibold text-red-800"
					>
						{changeError}
					</div>
				{/if}

				<form
					class="max-w-md space-y-4"
					onsubmit={(e) => {
						e.preventDefault();
						submitPassword();
					}}
				>
					<div>
						<label
							for="pw-current"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							Current Password <span class="text-red-500">*</span>
						</label>
						<input
							id="pw-current"
							type="password"
							bind:value={currentPassword}
							required
							autocomplete="current-password"
							placeholder="••••••••"
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div>
						<label
							for="pw-new"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							New Password <span class="text-red-500">*</span>
						</label>
						<input
							id="pw-new"
							type="password"
							bind:value={newPassword}
							required
							minlength="8"
							autocomplete="new-password"
							placeholder="••••••••"
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div>
						<label
							for="pw-confirm"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							Confirm New Password <span class="text-red-500">*</span>
						</label>
						<input
							id="pw-confirm"
							type="password"
							bind:value={confirmPassword}
							required
							minlength="8"
							autocomplete="new-password"
							placeholder="••••••••"
							class="mt-1.5 block w-full rounded-lg border-slate-300 px-3 py-2.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div class="pt-2">
						<button
							type="submit"
							disabled={changing}
							aria-busy={changing}
							class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60"
						>
							{#if changing}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
							Update Password
						</button>
					</div>
				</form>
			</div>
		</section>
	{/if}
</div>
