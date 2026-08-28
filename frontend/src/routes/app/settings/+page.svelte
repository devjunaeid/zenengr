<script>
	import { untrack } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { ApiError, assetUrl } from '$lib/api/client.js';
	import * as tenantApi from '$lib/api/tenant.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import Icon from '@iconify/svelte';
	import domain from '@iconify-icons/mdi/domain';
	import imageOutline from '@iconify-icons/mdi/image-outline';
	import paletteOutline from '@iconify-icons/mdi/palette-outline';

	let { data } = $props();

	const token = auth.token;
	let isAdmin = $derived(auth.can('manage', 'tenant_settings'));

	let businessName = $state(untrack(() => data.profile.business_name));
	let contactPhone = $state(untrack(() => data.profile.contact_info?.phone ?? ''));
	let brandingColor = $state(untrack(() => data.profile.branding?.color ?? '#4F46E5'));
	let profileBusy = $state(false);
	let profileMsg = $state(null);
	let profileErr = $state(null);

	let logoFile = $state(null);
	let clientPreview = $state(null);
	let logoBusy = $state(false);
	let logoMsg = $state(null);
	let logoErr = $state(null);
	let logoTimestamp = $state(Date.now());
	let logoUrl = $state(untrack(() => data.profile.branding?.logo_url ?? null));

	function onFileSelected(e) {
		const file = e.currentTarget.files?.[0] ?? null;
		logoFile = file;
		logoErr = null;
		if (file) {
			clientPreview = URL.createObjectURL(file);
		} else {
			clientPreview = null;
		}
	}

	async function uploadLogo() {
		if (!logoFile) {
			logoErr = 'Select an image file first.';
			return;
		}
		logoBusy = true;
		logoMsg = null;
		logoErr = null;
		try {
			const res = await tenantApi.uploadLogo(fetch, token, logoFile);
			logoUrl = res.logo_url;
			logoTimestamp = Date.now();
			clientPreview = null;
			logoFile = null;
			logoMsg = 'Logo updated successfully.';
			setTimeout(() => (logoMsg = null), 4000);
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
			profileMsg = 'Business profile saved.';
			setTimeout(() => (profileMsg = null), 3000);
			await invalidateAll();
		} catch (e) {
			profileErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			profileBusy = false;
		}
	}
</script>

<svelte:head><title>Business Profile — ZenEngr</title></svelte:head>

<div class="space-y-6">
	<!-- Business Profile Form Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
			<div class="flex items-center gap-2.5">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
					<Icon icon={domain} class="h-4 w-4" />
				</div>
				<div>
					<h2 class="text-sm font-bold text-slate-900">Organization Profile</h2>
					<p class="text-xs text-slate-500">Official business identity displayed across invoices and client portals.</p>
				</div>
			</div>
		</div>

		<div class="p-6">
			{#if profileMsg}
				<div role="status" class="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-800">
					✓ {profileMsg}
				</div>
			{/if}
			{#if profileErr}
				<div role="alert" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs font-semibold text-red-800">
					{profileErr}
				</div>
			{/if}

			<form
				class="space-y-5"
				onsubmit={(e) => {
					e.preventDefault();
					saveProfile();
				}}
			>
				<div class="grid gap-5 sm:grid-cols-2">
					<div class="sm:col-span-2">
						<label for="sp-name" class="block text-xs font-semibold uppercase tracking-wider text-slate-700">
							Business Name <span class="text-red-500">*</span>
						</label>
						<input
							id="sp-name"
							type="text"
							bind:value={businessName}
							required
							maxlength="255"
							disabled={!isAdmin}
							placeholder="e.g. ZenEngr Solutions Inc."
							class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500 py-2.5 px-3"
						/>
					</div>

					<div>
						<label for="sp-phone" class="block text-xs font-semibold uppercase tracking-wider text-slate-700">
							Contact / Support Phone
						</label>
						<input
							id="sp-phone"
							type="text"
							bind:value={contactPhone}
							disabled={!isAdmin}
							placeholder="+1 (555) 000-0000"
							class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500 py-2.5 px-3"
						/>
					</div>

					<div>
						<label for="sp-color" class="block text-xs font-semibold uppercase tracking-wider text-slate-700">
							Primary Brand Color
						</label>
						<div class="mt-1.5 flex items-center gap-2">
							<input
								type="color"
								bind:value={brandingColor}
								disabled={!isAdmin}
								class="h-10 w-12 cursor-pointer rounded-lg border border-slate-300 bg-white p-1 shadow-2xs"
							/>
							<input
								id="sp-color"
								type="text"
								bind:value={brandingColor}
								placeholder="#4F46E5"
								disabled={!isAdmin}
								class="block w-full font-mono uppercase rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500 py-2.5 px-3"
							/>
						</div>
					</div>
				</div>

				{#if isAdmin}
					<div class="flex justify-end border-t border-slate-100 pt-5">
						<button
							type="submit"
							disabled={profileBusy}
							aria-busy={profileBusy}
							class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
						>
							{#if profileBusy}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
							Save Profile Changes
						</button>
					</div>
				{/if}
			</form>
		</div>
	</section>

	<!-- Brand Logo Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
			<div class="flex items-center gap-2.5">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
					<Icon icon={imageOutline} class="h-4 w-4" />
				</div>
				<div>
					<h2 class="text-sm font-bold text-slate-900">Brand Logo</h2>
					<p class="text-xs text-slate-500">Visible in top navigation, email receipts, and invoice PDFs.</p>
				</div>
			</div>
		</div>

		<div class="p-6">
			{#if logoMsg}
				<div role="status" class="mb-5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-800">
					✓ {logoMsg}
				</div>
			{/if}
			{#if logoErr}
				<div role="alert" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs font-semibold text-red-800">
					{logoErr}
				</div>
			{/if}

			<div class="flex flex-col gap-6 sm:flex-row sm:items-center">
				<!-- Logo Preview -->
				<div class="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 p-2">
					{#if clientPreview}
						<img
							src={clientPreview}
							alt="Selected Logo Preview"
							class="h-full w-full object-contain"
						/>
					{:else if logoUrl}
						<img
							src={`${assetUrl(logoUrl)}?t=${logoTimestamp}`}
							alt="Company Logo"
							class="h-full w-full object-contain"
						/>
					{:else}
						<Icon icon={imageOutline} class="h-8 w-8 text-slate-300" />
					{/if}
				</div>

				<!-- Upload Inputs -->
				<div class="flex-1 space-y-3">
					<label for="sp-logo" class="block text-xs font-semibold uppercase tracking-wider text-slate-700">
						Upload New Logo File
					</label>
					<p class="text-xs text-slate-500">Supports PNG, JPEG, WebP, GIF, or SVG (Max 5MB).</p>
					{#if isAdmin}
						<div class="flex flex-wrap items-center gap-3">
							<input
								id="sp-logo"
								type="file"
								accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml,.png,.jpg,.jpeg,.webp,.gif,.svg"
								onchange={onFileSelected}
								class="block text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-slate-700 hover:file:bg-slate-200 cursor-pointer"
							/>
							{#if logoFile}
								<button
									type="button"
									disabled={logoBusy}
									aria-busy={logoBusy}
									onclick={uploadLogo}
									class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 disabled:opacity-60 transition-colors cursor-pointer"
								>
									{#if logoBusy}<Spinner class="h-3 w-3 text-white" />{/if}
									Upload Logo
								</button>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</section>
</div>
