<script>
	import { untrack } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import * as adminApi from '$lib/api/admin.js';
	import { ApiError } from '$lib/api/client.js';
	import AuditLogList from '$lib/components/AuditLogList.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import ScrollableTabs from '$lib/components/ScrollableTabs.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { AUDIT_ACTION_OPTIONS } from '$lib/utils/audit.js';
	import { formatDate, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	const tenantId = untrack(() => data.tenant.id);

	// ---- Active tab ----
	/** @type {'overview'|'subscription'|'users'|'flags'|'settings'} */
	let activeTab = $state('overview');

	const tabs = [
		{ id: 'overview', label: 'Overview' },
		{ id: 'subscription', label: 'Subscription' },
		{ id: 'users', label: 'Users' },
		{ id: 'flags', label: 'Feature Flags' },
		{ id: 'settings', label: 'Settings' },
		{ id: 'audit', label: 'Audit Log' }
	];

	// ---- Profile form ----
	let businessName = $state(untrack(() => data.tenant.business_name));
	let contactPhone = $state(untrack(() => data.tenant.contact_info?.phone ?? ''));
	let brandingColor = $state(untrack(() => data.tenant.branding?.color ?? ''));
	let logoUrl = $state(untrack(() => data.tenant.logo_url ?? ''));
	let profileBusy = $state(false);
	/** @type {string|null} */
	let profileMsg = $state(null);
	/** @type {string|null} */
	let profileErr = $state(null);

	async function saveProfile() {
		profileBusy = true;
		profileMsg = null;
		profileErr = null;
		try {
			await adminApi.updateTenant(fetch, token, tenantId, {
				business_name: businessName,
				contact_info: { ...data.tenant.contact_info, phone: contactPhone },
				branding: { ...data.tenant.branding, color: brandingColor },
				logo_url: logoUrl || null
			});
			profileMsg = 'Profile saved.';
			await invalidateAll();
		} catch (e) {
			profileErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			profileBusy = false;
		}
	}

	// ---- Subscription form ----
	let subPlanId = $state(untrack(() => data.subscription?.plan_id ?? data.tenant.plan_id));
	let subStatus = $state(untrack(() => data.subscription?.status ?? 'trialing'));
	let subCycle = $state(untrack(() => data.subscription?.billing_cycle ?? 'monthly'));
	let subRenewal = $state(untrack(() => data.subscription?.renewal_date ?? ''));
	let subBusy = $state(false);
	/** @type {string|null} */
	let subMsg = $state(null);
	/** @type {string|null} */
	let subErr = $state(null);

	async function saveSubscription() {
		subBusy = true;
		subMsg = null;
		subErr = null;
		try {
			await adminApi.updateSubscription(fetch, token, tenantId, {
				plan_id: subPlanId,
				status: subStatus,
				billing_cycle: subCycle,
				renewal_date: subRenewal || null
			});
			subMsg = 'Subscription saved.';
			await invalidateAll();
		} catch (e) {
			subErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			subBusy = false;
		}
	}

	// ---- Feature flags ----
	let newFlagKey = $state('');
	let newFlagEnabled = $state(true);
	/** @type {string|null} */
	let flagErr = $state(null);

	let overrideKeys = $derived(new Set(data.flags.overrides.map((f) => f.key)));

	/**
	 * @param {string} key
	 * @param {boolean} enabled
	 */
	async function setFlag(key, enabled) {
		flagErr = null;
		try {
			await adminApi.putFlag(fetch, token, tenantId, key, enabled);
			await invalidateAll();
		} catch (e) {
			flagErr = e instanceof ApiError ? e.message : 'Flag update failed.';
		}
	}

	/** @param {string} key */
	async function removeFlag(key) {
		flagErr = null;
		try {
			await adminApi.deleteFlag(fetch, token, tenantId, key);
			await invalidateAll();
		} catch (e) {
			flagErr = e instanceof ApiError ? e.message : 'Flag removal failed.';
		}
	}

	async function addFlag() {
		const key = newFlagKey.trim();
		if (!key) return;
		await setFlag(key, newFlagEnabled);
		newFlagKey = '';
	}

	// ---- Settings ----
	/** @type {Record<string, string>} */
	let settingDrafts = $state(
		untrack(() => Object.fromEntries(data.settings.map((s) => [s.key, s.value ?? ''])))
	);
	/** @type {string|null} */
	let savingSettingKey = $state(null);
	/** @type {Record<string, string>} */
	let savedSettingKeys = $state({});
	/** @type {string|null} */
	let settingErr = $state(null);

	/** @param {string} key */
	async function saveSetting(key) {
		settingErr = null;
		savingSettingKey = key;
		try {
			const raw = settingDrafts[key];
			const value = raw === '' ? null : raw;
			await adminApi.updateTenantSetting(fetch, token, tenantId, key, value);
			savedSettingKeys = { ...savedSettingKeys, [key]: 'Saved.' };
			setTimeout(() => {
				const next = { ...savedSettingKeys };
				delete next[key];
				savedSettingKeys = next;
			}, 3000);
			await invalidateAll();
		} catch (e) {
			settingErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			savingSettingKey = null;
		}
	}

	// ---- Lifecycle ----
	/** @type {'suspend'|'reactivate'|'cancel'|null} */
	let pendingAction = $state(null);
	let actionBusy = $state(false);
	/** @type {string|null} */
	let actionErr = $state(null);

	const actionText = {
		suspend: {
			title: 'Suspend tenant',
			description:
				'All users of this tenant will be blocked from signing in until the tenant is reactivated.',
			confirm: 'Suspend'
		},
		reactivate: {
			title: 'Reactivate tenant',
			description: 'The tenant and its users will regain access immediately.',
			confirm: 'Reactivate'
		},
		cancel: {
			title: 'Cancel tenant',
			description:
				'Cancellation is a terminal lifecycle action. The tenant will lose access permanently.',
			confirm: 'Cancel tenant'
		}
	};

	async function runLifecycle() {
		if (!pendingAction) return;
		actionBusy = true;
		actionErr = null;
		try {
			await adminApi.tenantLifecycle(fetch, token, tenantId, pendingAction);
			pendingAction = null;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Action failed.';
		} finally {
			actionBusy = false;
		}
	}

	// ---- Audit pagination ----
	let auditAction = $state(untrack(() => data.auditAction));

	/** @param {number} page */
	function gotoAuditPage(page) {
		const url = `${resolve('/admin/tenants/[id]', { id: tenantId })}?action=${encodeURIComponent(auditAction)}&apage=${page}`;
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(url);
	}

	function applyAuditAction() {
		gotoAuditPage(1);
	}

	// ---- Password reset ----
	/** @type {string|null} */
	let resetUserId = $state(null);
	let resetPassword = $state('');
	let resetBusy = $state(false);
	/** @type {string|null} */
	let resetMsg = $state(null);
	/** @type {string|null} */
	let resetErr = $state(null);
	let resetVisible = $state(false);

	/** @param {string} userId */
	function openReset(userId) {
		resetUserId = userId;
		resetPassword = '';
		resetMsg = null;
		resetErr = null;
		resetVisible = true;
	}

	async function submitReset() {
		if (!resetUserId || resetBusy) return;
		resetBusy = true;
		resetMsg = null;
		resetErr = null;
		try {
			await adminApi.resetTenantUserPassword(fetch, token, tenantId, resetUserId, resetPassword);
			resetMsg = 'Password reset successfully.';
			resetPassword = '';
		} catch (e) {
			resetErr = e instanceof ApiError ? e.message : 'Reset failed.';
		} finally {
			resetBusy = false;
		}
	}
</script>

<svelte:head><title>{data.tenant.business_name} — Super Admin</title></svelte:head>

<nav class="text-sm text-slate-500" aria-label="Breadcrumb">
	<a href={resolve('/admin/tenants')} class="text-indigo-600 hover:text-indigo-500">Tenants</a>
	<span aria-hidden="true"> / </span>
	<span>{data.tenant.business_name}</span>
</nav>

<div class="mt-2 flex flex-wrap items-center gap-3">
	<h1 class="text-2xl font-semibold text-slate-900">{data.tenant.business_name}</h1>
	<StatusBadge status={data.tenant.status} />
</div>
<p class="mt-1 text-sm text-slate-500">
	Slug <span class="font-mono">{data.tenant.slug}</span> · Plan {data.tenant.plan_name} · Created
	{formatDate(data.tenant.created_at)}
</p>

<!-- Tab bar -->
<div class="mt-6">
	<ScrollableTabs ariaLabel="Tenant management tabs">
		{#each tabs as tab (tab.id)}
			{@const active = activeTab === tab.id}
			<button
				type="button"
				onclick={() => (activeTab = tab.id)}
				class="inline-flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all {active
					? 'bg-indigo-600 text-white shadow-2xs'
					: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
				aria-current={active ? 'page' : undefined}
			>
				{#if tab.id === 'overview'}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}"
					>
						<path
							fill-rule="evenodd"
							d="M4 16.5v-13h-.25a.75.75 0 010-1.5h12.5a.75.75 0 010 1.5H16v13h.25a.75.75 0 010 1.5h-3.5a.75.75 0 01-.75-.75v-2.5a.75.75 0 00-.75-.75h-2.5a.75.75 0 00-.75.75v2.5a.75.75 0 01-.75.75h-3.5a.75.75 0 010-1.5H4zm3-11a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1zm.5 2.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zm2.5-.5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1zm.5 2.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1z"
							clip-rule="evenodd"
						/>
					</svg>
				{:else if tab.id === 'subscription'}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}"
					>
						<path
							fill-rule="evenodd"
							d="M2.5 4A1.5 1.5 0 001 5.5V6h18v-.5A1.5 1.5 0 0017.5 4h-15zM19 8.5H1v6A1.5 1.5 0 002.5 16h15a1.5 1.5 0 001.5-1.5v-6zM3 13.25a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5a.75.75 0 01-.75-.75zm4.75-.75a.75.75 0 000 1.5h3.5a.75.75 0 000-1.5h-3.5z"
							clip-rule="evenodd"
						/>
					</svg>
				{:else if tab.id === 'users'}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}"
					>
						<path
							d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z"
						/>
					</svg>
				{:else if tab.id === 'flags'}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}"
					>
						<path
							d="M3.5 2.75a.75.75 0 00-1.5 0v14.5a.75.75 0 001.5 0v-4.392l1.657-.348a6.449 6.449 0 014.271.572 7.948 7.948 0 005.965.524l2.078-.64A.75.75 0 0018 12.25v-8.5a.75.75 0 00-.904-.734l-2.38.501a7.25 7.25 0 01-4.186-.363l-.502-.2a8.75 8.75 0 00-5.053-.439l-1.475.31V2.75z"
						/>
					</svg>
				{:else if tab.id === 'settings'}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}"
					>
						<path
							fill-rule="evenodd"
							d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
							clip-rule="evenodd"
						/>
					</svg>
				{:else if tab.id === 'audit'}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}"
					>
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z"
							clip-rule="evenodd"
						/>
					</svg>
				{/if}
				<span>{tab.label}</span>
				{#if tab.id === 'users'}
					<span
						class="ml-0.5 rounded-full px-1.5 py-0.2 text-[10px] font-bold {active
							? 'bg-indigo-700/80 text-white'
							: 'bg-slate-100 text-slate-600'}"
					>
						{data.users.length}
					</span>
				{/if}
			</button>
		{/each}
	</ScrollableTabs>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: Overview -->
<!-- ═══════════════════════════════════════════════════════════════ -->
{#if activeTab === 'overview'}
	<!-- Profile form -->
	<section
		class="mt-6 max-w-xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="profile-h"
	>
		<h2 id="profile-h" class="flex items-center gap-2 text-base font-semibold text-slate-900">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-4 w-4 text-slate-400"
			>
				<path
					fill-rule="evenodd"
					d="M4 16.5v-13h-.25a.75.75 0 010-1.5h12.5a.75.75 0 010 1.5H16v13h.25a.75.75 0 010 1.5h-3.5a.75.75 0 01-.75-.75v-2.5a.75.75 0 00-.75-.75h-2.5a.75.75 0 00-.75.75v2.5a.75.75 0 01-.75.75h-3.5a.75.75 0 010-1.5H4z"
					clip-rule="evenodd"
				/>
			</svg>
			Profile
		</h2>
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
				<label for="p-name" class="block text-sm font-medium text-slate-700">Business name</label>
				<input
					id="p-name"
					type="text"
					bind:value={businessName}
					required
					maxlength="255"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="p-phone" class="block text-sm font-medium text-slate-700">Contact phone</label>
				<input
					id="p-phone"
					type="text"
					bind:value={contactPhone}
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="p-color" class="block text-sm font-medium text-slate-700">Brand color</label>
					<input
						id="p-color"
						type="text"
						bind:value={brandingColor}
						placeholder="#4F46E5"
						class="mt-1 block w-full rounded-md border-slate-300 font-mono text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="p-logo" class="block text-sm font-medium text-slate-700">Logo URL</label>
					<input
						id="p-logo"
						type="url"
						bind:value={logoUrl}
						placeholder="https://…"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
			<button
				type="submit"
				disabled={profileBusy}
				aria-busy={profileBusy}
				class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if profileBusy}<Spinner class="h-4 w-4 text-white" />{/if}
				Save profile
			</button>
		</form>
	</section>

	<!-- Lifecycle -->
	<section class="mt-6" aria-labelledby="life-h">
		<h2 id="life-h" class="flex items-center gap-2 text-sm font-semibold text-slate-700">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-4 w-4 text-slate-400"
			>
				<path
					fill-rule="evenodd"
					d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 00.374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.39-.223-2.73-.635-3.985a.75.75 0 00-.722-.516l-.143.001c-2.996 0-5.717-1.17-7.734-3.08z"
					clip-rule="evenodd"
				/>
			</svg>
			Lifecycle
			<span class="font-normal text-slate-500">— <StatusBadge status={data.tenant.status} /></span>
		</h2>
		{#if actionErr}
			<p
				role="alert"
				class="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{actionErr}
			</p>
		{/if}
		<div class="mt-3 flex flex-wrap gap-3">
			{#if data.tenant.status === 'active' || data.tenant.status === 'trial'}
				<button
					type="button"
					onclick={() => (pendingAction = 'suspend')}
					class="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-100 focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:outline-none"
				>
					Suspend
				</button>
			{/if}
			{#if data.tenant.status === 'suspended'}
				<button
					type="button"
					onclick={() => (pendingAction = 'reactivate')}
					class="rounded-md border border-green-300 bg-green-50 px-4 py-2 text-sm font-medium text-green-800 hover:bg-green-100 focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:outline-none"
				>
					Reactivate
				</button>
			{/if}
			{#if data.tenant.status !== 'cancelled'}
				<button
					type="button"
					onclick={() => (pendingAction = 'cancel')}
					class="rounded-md border border-red-300 bg-red-50 px-4 py-2 text-sm font-medium text-red-800 hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
				>
					Cancel tenant
				</button>
			{/if}
		</div>
	</section>
{/if}

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: Subscription -->
<!-- ═══════════════════════════════════════════════════════════════ -->
{#if activeTab === 'subscription'}
	<section
		class="mt-6 max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="sub-h"
	>
		<h2 id="sub-h" class="flex items-center gap-2 text-base font-semibold text-slate-900">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-4 w-4 text-slate-400"
			>
				<path
					fill-rule="evenodd"
					d="M2.5 4A1.5 1.5 0 001 5.5V6h18v-.5A1.5 1.5 0 0017.5 4h-15zM19 8.5H1v6A1.5 1.5 0 002.5 16h15a1.5 1.5 0 001.5-1.5v-6zM3 13.25a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5a.75.75 0 01-.75-.75zm4.75-.75a.75.75 0 000 1.5h3.5a.75.75 0 000-1.5h-3.5z"
					clip-rule="evenodd"
				/>
			</svg>
			Subscription
		</h2>
		{#if !data.subscription}
			<p class="mt-2 text-sm text-slate-500">
				No subscription record exists yet. Saving below assigns one for this tenant.
			</p>
		{/if}
		{#if subMsg}
			<p
				role="status"
				class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
			>
				{subMsg}
			</p>
		{/if}
		{#if subErr}
			<p
				role="alert"
				class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{subErr}
			</p>
		{/if}
		<form
			class="mt-4 space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				saveSubscription();
			}}
		>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="s-plan" class="block text-sm font-medium text-slate-700">Plan</label>
					<select
						id="s-plan"
						bind:value={subPlanId}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					>
						{#each data.plans as plan (plan.id)}
							<option value={plan.id}>{plan.name}{plan.is_active ? '' : ' (inactive)'}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="s-status" class="block text-sm font-medium text-slate-700">Status</label>
					<select
						id="s-status"
						bind:value={subStatus}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					>
						{#each ['trialing', 'active', 'past_due', 'cancelled'] as s (s)}
							<option value={s}>{humanize(s)}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="s-cycle" class="block text-sm font-medium text-slate-700">Billing cycle</label
					>
					<select
						id="s-cycle"
						bind:value={subCycle}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					>
						<option value="monthly">Monthly</option>
						<option value="yearly">Yearly</option>
					</select>
				</div>
				<div>
					<label for="s-renewal" class="block text-sm font-medium text-slate-700"
						>Renewal date</label
					>
					<input
						id="s-renewal"
						type="date"
						bind:value={subRenewal}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
			<button
				type="submit"
				disabled={subBusy}
				aria-busy={subBusy}
				class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if subBusy}<Spinner class="h-4 w-4 text-white" />{/if}
				Save subscription
			</button>
		</form>
	</section>
{/if}

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: Users -->
<!-- ═══════════════════════════════════════════════════════════════ -->
{#if activeTab === 'users'}
	<div class="mt-6">
		<div class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
			<div class="flex items-center justify-between border-b border-slate-200 px-6 py-4">
				<div>
					<h2 class="flex items-center gap-2 text-base font-semibold text-slate-900">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="h-4 w-4 text-slate-400"
						>
							<path
								d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z"
							/>
						</svg>
						Admin Users
					</h2>
					<p class="mt-0.5 text-sm text-slate-500">
						{data.users.length} user{data.users.length === 1 ? '' : 's'} in this tenant
					</p>
				</div>
			</div>

			{#if data.users.length === 0}
				<p class="px-6 py-8 text-sm text-slate-500">No admin users found for this tenant.</p>
			{:else}
				<!-- Mobile cards (< md): clearly separated distinct cards -->
				<div class="space-y-3 p-3 bg-slate-50/60 md:hidden">
					{#each data.users as user (user.id)}
						<div class="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 transition-shadow hover:shadow-xs">
							<div class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<div class="text-sm font-semibold text-slate-900">{user.full_name}</div>
									<div class="text-xs text-slate-500">{user.email}</div>
								</div>
								<span
									class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset
									{user.role === 'admin'
										? 'bg-indigo-50 text-indigo-700 ring-indigo-600/20'
										: 'bg-slate-100 text-slate-700 ring-slate-500/20'}"
								>
									{humanize(user.role)}
								</span>
							</div>

							<div class="flex items-center justify-between text-xs text-slate-500">
								<span
									class="inline-flex items-center gap-1.5 font-medium
									{user.is_active ? 'text-green-700' : 'text-slate-400'}"
								>
									<span
										class="inline-block h-1.5 w-1.5 rounded-full {user.is_active
											? 'bg-green-500'
											: 'bg-slate-300'}"
									></span>
									{user.is_active ? 'Active' : 'Inactive'}
								</span>
								<span>Created {formatDate(user.created_at)}</span>
							</div>

							<div class="flex justify-end pt-1">
								<button
									type="button"
									onclick={() => openReset(user.id)}
									class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="h-3.5 w-3.5"
									>
										<path
											fill-rule="evenodd"
											d="M8 1a3.5 3.5 0 00-3.5 3.5V7A1.5 1.5 0 003 8.5v5A1.5 1.5 0 004.5 15h7a1.5 1.5 0 001.5-1.5v-5A1.5 1.5 0 0011.5 7V4.5A3.5 3.5 0 008 1zm2 6V4.5a2 2 0 10-4 0V7h4z"
											clip-rule="evenodd"
										/>
									</svg>
									Reset password
								</button>
							</div>
						</div>
					{/each}
				</div>

				<!-- Desktop table (>= md) -->
				<div class="relative hidden overflow-x-auto md:block">
					<table class="min-w-full divide-y divide-slate-200">
						<thead class="bg-slate-50">
							<tr>
								<th
									scope="col"
									class="px-6 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Name / Email</th
								>
								<th
									scope="col"
									class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Role</th
								>
								<th
									scope="col"
									class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Status</th
								>
								<th
									scope="col"
									class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Created</th
								>
								<th scope="col" class="px-4 py-3"><span class="sr-only">Actions</span></th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-200">
							{#each data.users as user (user.id)}
								<tr class="hover:bg-slate-50">
									<td class="px-6 py-3">
										<div class="text-sm font-medium text-slate-900">{user.full_name}</div>
										<div class="text-xs text-slate-500">{user.email}</div>
									</td>
									<td class="px-4 py-3">
										<span
											class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset
										{user.role === 'admin'
												? 'bg-indigo-50 text-indigo-700 ring-indigo-600/20'
												: 'bg-slate-100 text-slate-700 ring-slate-500/20'}"
										>
											{humanize(user.role)}
										</span>
									</td>
									<td class="px-4 py-3">
										<span
											class="inline-flex items-center gap-1.5 text-xs font-medium
										{user.is_active ? 'text-green-700' : 'text-slate-400'}"
										>
											<span
												class="inline-block h-1.5 w-1.5 rounded-full {user.is_active
													? 'bg-green-500'
													: 'bg-slate-300'}"
											></span>
											{user.is_active ? 'Active' : 'Inactive'}
										</span>
									</td>
									<td class="px-4 py-3 text-sm text-slate-500">{formatDate(user.created_at)}</td>
									<td class="px-4 py-3 text-right">
										<button
											type="button"
											onclick={() => openReset(user.id)}
											class="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="h-3.5 w-3.5"
											>
												<path
													fill-rule="evenodd"
													d="M8 1a3.5 3.5 0 00-3.5 3.5V7A1.5 1.5 0 003 8.5v5A1.5 1.5 0 004.5 15h7a1.5 1.5 0 001.5-1.5v-5A1.5 1.5 0 0011.5 7V4.5A3.5 3.5 0 008 1zm2 6V4.5a2 2 0 10-4 0V7h4z"
													clip-rule="evenodd"
												/>
											</svg>
											Reset password
										</button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>

		<!-- Password reset inline panel -->
		{#if resetVisible && resetUserId}
			{@const targetUser = data.users.find((u) => u.id === resetUserId)}
			<div class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-5">
				<div class="flex items-start justify-between gap-3">
					<div>
						<h3 class="flex items-center gap-2 text-sm font-semibold text-amber-900">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="h-4 w-4"
							>
								<path
									fill-rule="evenodd"
									d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
									clip-rule="evenodd"
								/>
							</svg>
							Reset password for {targetUser?.full_name ?? resetUserId}
						</h3>
						<p class="mt-0.5 text-xs text-amber-700">{targetUser?.email}</p>
					</div>
					<button
						type="button"
						onclick={() => (resetVisible = false)}
						class="text-amber-600 hover:text-amber-800"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="h-5 w-5"
						>
							<path
								d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
							/>
						</svg>
					</button>
				</div>

				{#if resetMsg}
					<p
						role="status"
						class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
					>
						{resetMsg}
					</p>
				{/if}
				{#if resetErr}
					<p
						role="alert"
						class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
					>
						{resetErr}
					</p>
				{/if}

				<form
					class="mt-4 flex items-end gap-3"
					onsubmit={(e) => {
						e.preventDefault();
						submitReset();
					}}
				>
					<div class="flex-1">
						<label for="reset-pw" class="block text-xs font-medium text-amber-900"
							>New password <span class="text-amber-600">(min 8 chars)</span></label
						>
						<input
							id="reset-pw"
							type="password"
							bind:value={resetPassword}
							required
							minlength="8"
							autocomplete="new-password"
							class="mt-1 block w-full rounded-md border-amber-300 text-sm shadow-sm focus:border-amber-500 focus:ring-amber-500"
						/>
					</div>
					<button
						type="submit"
						disabled={resetBusy || resetPassword.length < 8}
						aria-busy={resetBusy}
						class="inline-flex items-center gap-2 rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if resetBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Set password
					</button>
				</form>
			</div>
		{/if}
	</div>
{/if}

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: Feature Flags -->
<!-- ═══════════════════════════════════════════════════════════════ -->
{#if activeTab === 'flags'}
	<section
		class="mt-6 max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="flags-h"
	>
		<h2 id="flags-h" class="flex items-center gap-2 text-base font-semibold text-slate-900">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-4 w-4 text-slate-400"
			>
				<path
					d="M3.5 2.75a.75.75 0 00-1.5 0v14.5a.75.75 0 001.5 0v-4.392l1.657-.348a6.449 6.449 0 014.271.572 7.948 7.948 0 005.965.524l2.078-.64A.75.75 0 0018 12.25v-8.5a.75.75 0 00-.904-.734l-2.38.501a7.25 7.25 0 01-4.186-.363l-.502-.2a8.75 8.75 0 00-5.053-.439l-1.475.31V2.75z"
				/>
			</svg>
			Feature Flags
		</h2>
		{#if flagErr}
			<p
				role="alert"
				class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{flagErr}
			</p>
		{/if}
		{#if data.flags.resolved.length === 0}
			<p class="mt-2 text-sm text-slate-500">No flags defined for this tenant's plan.</p>
		{:else}
			<ul class="mt-3 divide-y divide-slate-200">
				{#each data.flags.resolved as flag (flag.key)}
					<li class="flex items-center justify-between gap-3 py-2.5">
						<div>
							<span class="font-mono text-sm text-slate-800">{flag.key}</span>
							{#if overrideKeys.has(flag.key)}
								<span
									class="ml-2 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800 ring-1 ring-indigo-600/20 ring-inset"
									>override</span
								>
							{/if}
						</div>
						<div class="flex items-center gap-2">
							<button
								type="button"
								role="switch"
								aria-checked={flag.enabled}
								aria-label={`Toggle ${flag.key}`}
								onclick={() => setFlag(flag.key, !flag.enabled)}
								class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none {flag.enabled
									? 'bg-indigo-600'
									: 'bg-slate-300'}"
							>
								<span
									class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {flag.enabled
										? 'translate-x-6'
										: 'translate-x-1'}"
								></span>
							</button>
							<span class="w-7 text-xs text-slate-500">{flag.enabled ? 'On' : 'Off'}</span>
							{#if overrideKeys.has(flag.key)}
								<button
									type="button"
									onclick={() => removeFlag(flag.key)}
									class="text-xs font-medium text-slate-500 underline hover:text-slate-700"
									aria-label={`Remove override for ${flag.key}`}>Reset</button
								>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
		<form
			class="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-200 pt-4"
			onsubmit={(e) => {
				e.preventDefault();
				addFlag();
			}}
		>
			<div>
				<label for="f-key" class="block text-xs font-medium text-slate-600">New flag key</label>
				<input
					id="f-key"
					type="text"
					bind:value={newFlagKey}
					placeholder="feature_key"
					class="mt-1 block w-48 rounded-md border-slate-300 font-mono text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<label class="flex items-center gap-2 text-sm text-slate-700">
				<input
					type="checkbox"
					bind:checked={newFlagEnabled}
					class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
				/>
				Enabled
			</label>
			<button
				type="submit"
				class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Add override
			</button>
		</form>
	</section>
{/if}

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: Settings & Audit -->
<!-- ═══════════════════════════════════════════════════════════════ -->
{#if activeTab === 'settings'}
	<!-- Settings -->
	<section
		class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
		aria-labelledby="settings-h"
	>
		<h2
			id="settings-h"
			class="flex items-center gap-2 border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-4 w-4 text-slate-400"
			>
				<path
					fill-rule="evenodd"
					d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
					clip-rule="evenodd"
				/>
			</svg>
			Settings
			<span class="ml-1 text-xs font-normal text-slate-500">Changes are audited.</span>
		</h2>
		{#if settingErr}
			<p
				role="alert"
				class="mx-6 mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{settingErr}
			</p>
		{/if}
		{#if data.settings.length === 0}
			<p class="px-6 py-8 text-sm text-slate-500">No settings defined for this tenant yet.</p>
		{:else}
			<!-- Mobile cards (< md): clearly separated distinct cards -->
			<div class="space-y-3 p-3 bg-slate-50/60 md:hidden">
				{#each data.settings as s (s.key)}
					<div class="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3 transition-shadow hover:shadow-xs">
						<div class="flex items-start justify-between gap-3">
							<span class="font-mono text-xs font-bold text-slate-800 break-all">{s.key}</span>
							<span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 shrink-0">
								{s.permission_level}
							</span>
						</div>
						<div>
							<label for="m-aset-{s.key}" class="sr-only">Value for {s.key}</label>
							<input
								id="m-aset-{s.key}"
								type="text"
								bind:value={settingDrafts[s.key]}
								class="block w-full rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>
						<div class="flex items-center justify-between pt-1">
							<div>
								{#if savedSettingKeys[s.key]}
									<span role="status" class="text-xs font-semibold text-green-700">
										✓ {savedSettingKeys[s.key]}
									</span>
								{/if}
							</div>
							<button
								type="button"
								disabled={savingSettingKey === s.key}
								aria-busy={savingSettingKey === s.key}
								onclick={() => saveSetting(s.key)}
								class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
							>
								{#if savingSettingKey === s.key}<Spinner class="h-3 w-3" />{/if}
								Save
							</button>
						</div>
					</div>
				{/each}
			</div>

			<!-- Desktop table (>= md) -->
			<div class="relative hidden overflow-x-auto md:block">
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
									<label for="aset-{s.key}" class="sr-only">Value for {s.key}</label>
									<input
										id="aset-{s.key}"
										type="text"
										bind:value={settingDrafts[s.key]}
										class="block w-64 max-w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
									/>
								</td>
								<td class="px-4 py-3 text-right">
									<button
										type="button"
										disabled={savingSettingKey === s.key}
										aria-busy={savingSettingKey === s.key}
										onclick={() => saveSetting(s.key)}
										class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
									>
										{#if savingSettingKey === s.key}<Spinner class="h-3.5 w-3.5" />{/if}
										Save
									</button>
									{#if savedSettingKeys[s.key]}
										<span role="status" class="ml-2 text-xs text-green-700"
											>{savedSettingKeys[s.key]}</span
										>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
{/if}

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: Audit Log -->
<!-- ═══════════════════════════════════════════════════════════════ -->
{#if activeTab === 'audit'}
	<section
		class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
		aria-labelledby="audit-h"
	>
		<div
			class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4"
		>
			<h2 id="audit-h" class="flex items-center gap-2 text-base font-semibold text-slate-900">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4 text-slate-400"
				>
					<path
						fill-rule="evenodd"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z"
						clip-rule="evenodd"
					/>
				</svg>
				Audit Log
			</h2>
			<form
				class="flex flex-wrap items-end gap-3"
				onsubmit={(e) => {
					e.preventDefault();
					applyAuditAction();
				}}
			>
				<div class="min-w-0 flex-1 sm:flex-none">
					<label for="f-audit-action" class="block text-xs font-medium text-slate-600">Action</label
					>
					<select
						id="f-audit-action"
						bind:value={auditAction}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:w-72"
					>
						<option value="">All actions</option>
						{#each AUDIT_ACTION_OPTIONS as group (group.group)}
							<optgroup label={group.group}>
								{#each group.items as item (item.value)}
									<option value={item.value}>{item.label}</option>
								{/each}
							</optgroup>
						{/each}
					</select>
				</div>
				<button
					type="submit"
					class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Apply
				</button>
			</form>
		</div>
		{#if data.audit.items.length === 0}
			<p class="px-6 py-8 text-sm text-slate-500">No audit events recorded for this tenant yet.</p>
		{:else}
			<AuditLogList entries={data.audit.items} linkPrefix={null} />
			<Pagination
				page={data.audit.page}
				pageSize={data.audit.page_size}
				total={data.audit.total}
				onpage={gotoAuditPage}
			/>
		{/if}
	</section>
{/if}

<!-- Confirm dialog for lifecycle actions -->
{#if pendingAction}
	<ConfirmDialog
		bind:open={
			() => pendingAction !== null,
			(v) => {
				if (!v) pendingAction = null;
			}
		}
		title={actionText[pendingAction].title}
		description={actionText[pendingAction].description}
		confirmLabel={actionText[pendingAction].confirm}
		destructive={pendingAction !== 'reactivate'}
		busy={actionBusy}
		onconfirm={runLifecycle}
	/>
{/if}
