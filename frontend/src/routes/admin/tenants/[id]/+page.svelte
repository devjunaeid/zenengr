<script>
	import { untrack } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import * as adminApi from '$lib/api/admin.js';
	import { ApiError } from '$lib/api/client.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, formatDateTime, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	const tenantId = untrack(() => data.tenant.id);

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

	// ---- Flags ----
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
	/** @param {number} page */
	function gotoAuditPage(page) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(`${resolve('/admin/tenants/[id]', { id: tenantId })}?apage=${page}`);
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

<div class="mt-6 grid gap-6 lg:grid-cols-2">
	<!-- Profile -->
	<section
		class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="profile-h"
	>
		<h2 id="profile-h" class="text-base font-semibold text-slate-900">Profile</h2>
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
	<section
		class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="life-h"
	>
		<h2 id="life-h" class="text-base font-semibold text-slate-900">Lifecycle</h2>
		<p class="mt-1 text-sm text-slate-500">
			Current status: <StatusBadge status={data.tenant.status} />
		</p>
		{#if actionErr}
			<p
				role="alert"
				class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{actionErr}
			</p>
		{/if}
		<div class="mt-4 flex flex-wrap gap-3">
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

	<!-- Subscription -->
	<section
		class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="sub-h"
	>
		<h2 id="sub-h" class="text-base font-semibold text-slate-900">Subscription</h2>
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

	<!-- Feature flags -->
	<section
		class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="flags-h"
	>
		<h2 id="flags-h" class="text-base font-semibold text-slate-900">Feature flags</h2>
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
									aria-label={`Remove override for ${flag.key}`}
								>
									Reset
								</button>
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
</div>

<!-- Settings -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="settings-h"
>
	<h2
		id="settings-h"
		class="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
	>
		Settings
		<span class="ml-2 text-xs font-normal text-slate-500">Settings changes are audited.</span>
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
								<label for="aset-{s.key}" class="sr-only">Value for {s.key}</label>
								<input
									id="aset-{s.key}"
									type="text"
									bind:value={settingDrafts[s.key]}
									class="block w-64 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
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

<!-- Audit log -->
<section
	class="mt-6 rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="audit-h"
>
	<h2
		id="audit-h"
		class="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
	>
		Audit log
	</h2>
	{#if data.audit.items.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No audit events recorded for this tenant yet.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>When</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Action</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Actor</th
						>
						<th
							scope="col"
							class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Entity</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.audit.items as row (row.id)}
						<tr>
							<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
								>{formatDateTime(row.created_at)}</td
							>
							<td class="px-4 py-3 font-mono text-sm text-slate-800">{row.action}</td>
							<td class="px-4 py-3 text-sm text-slate-600">{row.actor_type}</td>
							<td class="px-4 py-3 text-sm text-slate-600">{row.entity_type}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Pagination
			page={data.audit.page}
			pageSize={data.audit.page_size}
			total={data.audit.total}
			onpage={gotoAuditPage}
		/>
	{/if}
</section>

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
