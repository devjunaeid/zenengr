<script>
	import { untrack } from 'svelte';
	import { resolve } from '$app/paths';
	import { invalidateAll } from '$app/navigation';
	import { ApiError, assetUrl } from '$lib/api/client.js';
	import * as tenantApi from '$lib/api/tenant.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	let isAdmin = $derived(auth.isTenantAdmin);

	// ---- Profile form ----
	let businessName = $state(untrack(() => data.profile.business_name));
	let contactPhone = $state(untrack(() => data.profile.contact_info?.phone ?? ''));
	let brandingColor = $state(untrack(() => data.profile.branding?.color ?? ''));
	let profileBusy = $state(false);
	/** @type {string|null} */
	let profileMsg = $state(null);
	/** @type {string|null} */
	let profileErr = $state(null);

	// ---- Logo upload (TODO-011) ----
	let logoFile = $state(/** @type {File|null} */ (null));
	let logoBusy = $state(false);
	/** @type {string|null} */
	let logoMsg = $state(null);
	/** @type {string|null} */
	let logoErr = $state(null);
	/** @type {string|null} */
	let logoUrl = $state(untrack(() => data.profile.branding?.logo_url ?? null));

	async function uploadLogo() {
		if (!logoFile) {
			logoErr = 'Pick an image file first.';
			return;
		}
		logoBusy = true;
		logoMsg = null;
		logoErr = null;
		try {
			const res = await tenantApi.uploadLogo(fetch, token, logoFile);
			logoUrl = res.logo_url;
			logoFile = null;
			logoMsg = 'Logo updated.';
			await invalidateAll();
		} catch (e) {
			logoErr = e instanceof ApiError ? e.message : 'Upload failed.';
		} finally {
			logoBusy = false;
		}
	}

	async function saveProfile() {
		profileBusy = true;
		profileMsg = null;
		profileErr = null;
		try {
			await tenantApi.updateProfile(fetch, token, {
				business_name: businessName,
				contact_info: { ...data.profile.contact_info, phone: contactPhone },
				branding: { ...data.profile.branding, color: brandingColor }
			});
			profileMsg = 'Profile saved.';
			await invalidateAll();
		} catch (e) {
			profileErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			profileBusy = false;
		}
	}

	// ---- Settings table ----
	// Draft values keyed by setting key; masked (null) values start empty.
	/** @type {Record<string, string>} */
	let drafts = $state(
		untrack(() => Object.fromEntries(data.settings.map((s) => [s.key, s.value ?? ''])))
	);
	/** @type {string|null} */
	let savingKey = $state(null);
	/** @type {Record<string, string>} */
	let savedKeys = $state({});
	/** @type {string|null} */
	let settingsErr = $state(null);

	/** @param {string} key */
	async function saveSetting(key) {
		settingsErr = null;
		savingKey = key;
		try {
			await tenantApi.updateSetting(fetch, token, key, drafts[key]);
			savedKeys = { ...savedKeys, [key]: 'Saved.' };
			setTimeout(() => {
				const next = { ...savedKeys };
				delete next[key];
				savedKeys = next;
			}, 3000);
			await invalidateAll();
		} catch (e) {
			settingsErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			savingKey = null;
		}
	}
</script>

<svelte:head><title>Settings — ZenEngr</title></svelte:head>

<div class="flex items-center justify-between">
	<h1 class="text-2xl font-semibold text-slate-900">Settings</h1>
	<a
		href={resolve('/app/settings/plan')}
		class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
	>
		View plan &amp; usage
	</a>
</div>

<!-- Tenant profile -->
<section
	class="mt-6 max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="profile-h"
>
	<h2 id="profile-h" class="text-base font-semibold text-slate-900">Business profile</h2>
	{#if !isAdmin}
		<p class="mt-1 text-sm text-slate-500">Only tenant admins can edit the profile.</p>
	{/if}
	{#if profileMsg}
		<p
			role="status"
			class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
		>
			{profileMsg}
		</p>
	{/if}
	{#if profileErr}
		<p
			role="alert"
			class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{profileErr}
		</p>
	{/if}
	<form
		class="mt-4 space-y-4"
		onsubmit={(e) => {
			e.preventDefault();
			saveProfile();
		}}
	>
		<div>
			<label for="sp-name" class="block text-sm font-medium text-slate-700">Business name</label>
			<input
				id="sp-name"
				type="text"
				bind:value={businessName}
				required
				maxlength="255"
				disabled={!isAdmin}
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500"
			/>
		</div>
		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<label for="sp-phone" class="block text-sm font-medium text-slate-700">Contact phone</label>
				<input
					id="sp-phone"
					type="text"
					bind:value={contactPhone}
					disabled={!isAdmin}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500"
				/>
			</div>
			<div>
				<label for="sp-color" class="block text-sm font-medium text-slate-700">Brand color</label>
				<input
					id="sp-color"
					type="text"
					bind:value={brandingColor}
					placeholder="#4F46E5"
					disabled={!isAdmin}
					class="mt-1 block w-full rounded-md border-slate-300 font-mono text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500"
				/>
			</div>
		</div>
		{#if isAdmin}
			<button
				type="submit"
				disabled={profileBusy}
				aria-busy={profileBusy}
				class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if profileBusy}<Spinner class="h-4 w-4 text-white" />{/if}
				Save profile
			</button>
		{/if}
	</form>
</section>

<!-- Tenant logo -->
<section
	class="mt-6 max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="logo-h"
>
	<h2 id="logo-h" class="text-base font-semibold text-slate-900">Logo</h2>
	<p class="mt-1 text-sm text-slate-500">Shown in the app header. PNG, JPEG, WebP, or GIF.</p>
	{#if logoMsg}
		<p
			role="status"
			class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
		>
			{logoMsg}
		</p>
	{/if}
	{#if logoErr}
		<p
			role="alert"
			class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{logoErr}
		</p>
	{/if}
	<div class="mt-4 flex flex-wrap items-center gap-3">
		<input
			id="sp-logo"
			type="file"
			accept="image/png,image/jpeg,image/webp,image/gif"
			disabled={!isAdmin || logoBusy}
			onchange={(e) =>
				(logoFile = /** @type {HTMLInputElement} */ (e.currentTarget).files?.[0] ?? null)}
			class="block w-full max-w-xs text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
		/>
		<button
			type="button"
			disabled={!isAdmin || logoBusy || !logoFile}
			aria-busy={logoBusy}
			onclick={uploadLogo}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if logoBusy}<Spinner class="h-4 w-4 text-white" />{/if}
			Upload
		</button>
		{#if logoUrl}
			<img src={assetUrl(logoUrl)} alt="Current business logo" class="h-10 w-auto" />
		{/if}
	</div>
</section>

<!-- Tenant settings -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="settings-h"
>
	<h2
		id="settings-h"
		class="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
	>
		Configuration
	</h2>
	{#if settingsErr}
		<p
			role="alert"
			class="mx-6 mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{settingsErr}
		</p>
	{/if}
	{#if data.settings.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">
			No configurable settings defined for this tenant yet.
		</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Key</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Permission</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Value</th
						>
						<th scope="col" class="px-4 py-3"><span class="sr-only">Actions</span></th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.settings as s (s.key)}
						<tr>
							<td class="px-4 py-3 font-mono text-sm text-slate-800">{s.key}</td>
							<td class="px-4 py-3 text-sm text-slate-600">{s.permission_level}</td>
							<td class="px-4 py-3">
								{#if s.editable && isAdmin}
									<label for="set-{s.key}" class="sr-only">Value for {s.key}</label>
									<input
										id="set-{s.key}"
										type="text"
										bind:value={drafts[s.key]}
										placeholder={s.value === null ? '••••••' : ''}
										class="block w-64 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
									/>
								{:else}
									<span class="text-sm text-slate-600">{s.value ?? '••••••'}</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-right">
								{#if s.editable && isAdmin}
									<button
										type="button"
										disabled={savingKey === s.key}
										aria-busy={savingKey === s.key}
										onclick={() => saveSetting(s.key)}
										class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
									>
										{#if savingKey === s.key}<Spinner class="h-3.5 w-3.5" />{/if}
										Save
									</button>
									{#if savedKeys[s.key]}
										<span role="status" class="ml-2 text-xs text-green-700">{savedKeys[s.key]}</span
										>
									{/if}
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>
