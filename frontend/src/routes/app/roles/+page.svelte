<script>
	import { untrack } from 'svelte';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { Dialog } from 'bits-ui';
	import { ApiError } from '$lib/api/client.js';
	import * as rolesApi from '$lib/api/roles.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import Icon from '@iconify/svelte';
	import shieldAccount from '@iconify-icons/mdi/shield-account';
	import shieldCheck from '@iconify-icons/mdi/shield-check';
	import shieldOutline from '@iconify-icons/mdi/shield-outline';
	import plus from '@iconify-icons/mdi/plus';
	import refresh from '@iconify-icons/mdi/refresh';
	import trashCanOutline from '@iconify-icons/mdi/trash-can-outline';
	import magnify from '@iconify-icons/mdi/magnify';
	import checkAll from '@iconify-icons/mdi/check-all';
	import closeCircleOutline from '@iconify-icons/mdi/close-circle-outline';
	import folderOpen from '@iconify-icons/mdi/folder-open';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import accountGroup from '@iconify-icons/mdi/account-group';
	import cog from '@iconify-icons/mdi/cog';
	import file from '@iconify-icons/mdi/file';
	import tools from '@iconify-icons/mdi/tools';
	import cash from '@iconify-icons/mdi/cash';
	import comment from '@iconify-icons/mdi/comment';
	import close from '@iconify-icons/mdi/close';

	let { data } = $props();

	const token = auth.token;

	let roles = $state(untrack(() => data.roles ?? []));

	let selectedId = $state(
		untrack(() => data.roles.find((r) => r.name !== 'super_admin')?.id ?? '')
	);
	let role = $derived(roles.find((r) => r.id === selectedId) ?? null);

	let isAdminRole = $derived(role?.name === 'admin');
	let isSuperAdminRole = $derived(role?.name === 'super_admin');
	let canEdit = $derived(
		auth.can('manage', 'roles') && role != null && !isAdminRole && !isSuperAdminRole
	);
	let catalogOk = $derived(data.catalog.length > 0);

	let draftName = $state('');
	let draftDesc = $state('');
	let draftGranted = new SvelteSet();
	let permSearch = $state('');

	$effect(() => {
		const r = role;
		if (!r) return;
		draftName = r.name;
		draftDesc = r.description ?? '';
		draftGranted.clear();
		for (const p of r.permissions ?? []) {
			if (p.granted) draftGranted.add(`${p.action}.${p.resource}`);
		}
	});

	function getGroupIcon(groupName) {
		const g = groupName.toLowerCase();
		if (g.includes('project')) return folderOpen;
		if (g.includes('invoice')) return receiptText;
		if (g.includes('payment') || g.includes('advance')) return cash;
		if (g.includes('client')) return accountGroup;
		if (g.includes('user') || g.includes('team') || g.includes('staff')) return shieldAccount;
		if (g.includes('file')) return file;
		if (g.includes('service')) return tools;
		if (g.includes('comment')) return comment;
		return cog;
	}

	let groups = $derived.by(() => {
		const byGroup = new SvelteMap();
		for (const c of data.catalog) {
			const g = c.group || 'Other';
			const list = byGroup.get(g) ?? [];
			list.push(c);
			byGroup.set(g, list);
		}
		const out = [];
		for (const [group, items] of byGroup) {
			items.sort((a, b) => a.label.localeCompare(b.label));
			out.push({ group, items, icon: getGroupIcon(group) });
		}
		out.sort((a, b) => a.group.localeCompare(b.group));
		return out;
	});

	let filteredGroups = $derived.by(() => {
		const q = permSearch.toLowerCase().trim();
		if (!q) return groups;

		const out = [];
		for (const g of groups) {
			const groupMatch = g.group.toLowerCase().includes(q);
			const matchingItems = g.items.filter(
				(item) =>
					groupMatch ||
					item.label.toLowerCase().includes(q) ||
					item.action.toLowerCase().includes(q) ||
					item.resource.toLowerCase().includes(q)
			);
			if (matchingItems.length > 0) {
				out.push({ group: g.group, items: matchingItems, icon: g.icon });
			}
		}
		return out;
	});

	let grantedCount = $derived(draftGranted.size);
	let totalCatalogCount = $derived(data.catalog.length);

	function togglePerm(action, resource) {
		const key = `${action}.${resource}`;
		if (draftGranted.has(key)) draftGranted.delete(key);
		else draftGranted.add(key);
	}

	function grantGroup(items) {
		for (const item of items) {
			draftGranted.add(`${item.action}.${item.resource}`);
		}
	}

	function revokeGroup(items) {
		for (const item of items) {
			draftGranted.delete(`${item.action}.${item.resource}`);
		}
	}

	let saveBusy = $state(false);
	let saveErr = $state(null);
	let saveMsg = $state(null);

	async function saveRole() {
		const r = role;
		if (!r || !canEdit) return;
		saveBusy = true;
		saveErr = null;
		saveMsg = null;
		try {
			const permissions = data.catalog.map((c) => ({
				action: c.action,
				resource: c.resource,
				granted: draftGranted.has(`${c.action}.${c.resource}`)
			}));
			const body = { permissions };
			if (!r.is_system) {
				body.name = draftName.trim();
				body.description = draftDesc.trim() || null;
			}
			const updated = await rolesApi.updateRole(fetch, token, r.id, body);
			roles = roles.map((x) => (x.id === updated.id ? updated : x));
			saveMsg = 'Role permissions saved successfully.';
			setTimeout(() => (saveMsg = null), 4000);
		} catch (e) {
			saveErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			saveBusy = false;
		}
	}

	let resetBusy = $state(false);
	let resetErr = $state(null);

	async function resetRoleDefaults() {
		const r = role;
		if (!r || !r.is_system) return;
		resetBusy = true;
		resetErr = null;
		saveMsg = null;
		try {
			const updated = await rolesApi.resetRole(fetch, token, r.id);
			roles = roles.map((x) => (x.id === updated.id ? updated : x));
			saveMsg = 'Reset to system default permissions.';
			setTimeout(() => (saveMsg = null), 4000);
		} catch (e) {
			resetErr = e instanceof ApiError ? e.message : 'Reset failed.';
		} finally {
			resetBusy = false;
		}
	}

	let deleteOpen = $state(false);
	let deleteBusy = $state(false);
	let deleteErr = $state(null);

	async function runDelete() {
		const r = role;
		if (!r) return;
		deleteBusy = true;
		deleteErr = null;
		try {
			await rolesApi.deleteRole(fetch, token, r.id);
			deleteOpen = false;
			roles = roles.filter((x) => x.id !== r.id);
			selectedId = roles.find((x) => x.name !== 'super_admin')?.id ?? '';
			saveMsg = null;
		} catch (e) {
			deleteErr = e instanceof ApiError ? e.message : 'Delete failed.';
			deleteOpen = false;
		} finally {
			deleteBusy = false;
		}
	}

	let newOpen = $state(false);
	let newBusy = $state(false);
	let newErr = $state(null);
	let newName = $state('');
	let newDesc = $state('');
	let newGranted = new SvelteSet();
	let newPermSearch = $state('');

	function openNewRole() {
		newErr = null;
		newName = '';
		newDesc = '';
		newPermSearch = '';
		newGranted.clear();
		newOpen = true;
	}

	function toggleNewPerm(action, resource) {
		const key = `${action}.${resource}`;
		if (newGranted.has(key)) newGranted.delete(key);
		else newGranted.add(key);
	}

	function grantNewGroup(items) {
		for (const item of items) {
			newGranted.add(`${item.action}.${item.resource}`);
		}
	}

	function revokeNewGroup(items) {
		for (const item of items) {
			newGranted.delete(`${item.action}.${item.resource}`);
		}
	}

	async function submitNewRole() {
		newErr = null;
		if (!newName.trim()) {
			newErr = 'Please enter a role name.';
			return;
		}
		newBusy = true;
		try {
			const permissions = data.catalog.map((c) => ({
				action: c.action,
				resource: c.resource,
				granted: newGranted.has(`${c.action}.${c.resource}`)
			}));
			const created = await rolesApi.createRole(fetch, token, {
				name: newName.trim(),
				description: newDesc.trim() || null,
				permissions
			});
			newOpen = false;
			roles = [...roles, created];
			selectedId = created.id;
			saveMsg = `Custom role "${created.name}" created.`;
			setTimeout(() => (saveMsg = null), 4000);
		} catch (e) {
			newErr = e instanceof ApiError ? e.message : 'Create failed.';
		} finally {
			newBusy = false;
		}
	}
</script>

<svelte:head><title>Roles &amp; Permissions — ZenEngr</title></svelte:head>

<div class="space-y-6">
	<!-- Page Header Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex items-center gap-3">
				<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
					<Icon icon={shieldAccount} class="h-5 w-5" />
				</div>
				<div>
					<h1 class="text-base font-bold text-slate-900">Roles &amp; Permissions</h1>
					<p class="text-xs text-slate-500 mt-0.5">
						Configure granular access control, member permissions, and operational security scopes.
					</p>
				</div>
			</div>

			<div class="flex items-center gap-3">
				<span class="inline-flex items-center rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">
					{roles.length} {roles.length === 1 ? 'configured role' : 'configured roles'}
				</span>

				{#if auth.can('manage', 'roles')}
					<button
						type="button"
						onclick={openNewRole}
						class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition-colors"
					>
						<Icon icon={plus} class="h-3.5 w-3.5" />
						Create Custom Role
					</button>
				{/if}
			</div>
		</div>
	</section>

	<!-- Notifications & Alert Banners -->
	{#if deleteErr || saveErr || resetErr}
		<div
			role="alert"
			class="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-800 shadow-2xs"
		>
			{deleteErr ?? saveErr ?? resetErr}
		</div>
	{/if}
	{#if saveMsg}
		<div
			role="status"
			class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs font-semibold text-emerald-800 shadow-2xs"
		>
			{saveMsg}
		</div>
	{/if}

	<!-- Main Two-Column Layout -->
	<div class="grid gap-6 lg:grid-cols-[18rem_1fr] items-start">
		<!-- Role Selection Sidebar Card -->
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs" aria-labelledby="roles-sidebar-h">
			<div class="border-b border-slate-100 bg-slate-50/50 px-4 py-3">
				<h2 id="roles-sidebar-h" class="text-xs font-bold uppercase tracking-wider text-slate-500">
					Available Roles
				</h2>
			</div>

			<ul class="divide-y divide-slate-100">
				{#each roles as r (r.id)}
					{@const active = r.id === selectedId}
					<li>
						<button
							type="button"
							onclick={() => (selectedId = r.id)}
							aria-pressed={active}
							class="group relative flex w-full flex-col px-4 py-3.5 text-left transition-colors {active
								? 'bg-indigo-50/60'
								: 'hover:bg-slate-50/80'}"
						>
							{#if active}
								<div class="absolute inset-y-0 left-0 w-1 bg-indigo-600 rounded-r"></div>
							{/if}

							<div class="flex items-center justify-between gap-2">
								<div class="flex items-center gap-2 min-w-0">
									<div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md {r.name === 'admin' ? 'bg-purple-100 text-purple-700' : active ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500'}">
										<Icon icon={r.name === 'admin' ? shieldCheck : shieldOutline} class="h-3.5 w-3.5" />
									</div>
									<span class="truncate text-xs font-bold capitalize {active ? 'text-indigo-950' : 'text-slate-800'}">
										{r.name}
									</span>
								</div>

								<span
									class="inline-flex shrink-0 rounded-md px-2 py-0.5 text-[10px] font-semibold {r.is_system
										? 'bg-slate-100 text-slate-600'
										: 'bg-indigo-100 text-indigo-700'}"
								>
									{r.is_system ? 'System' : 'Custom'}
								</span>
							</div>

							{#if r.description}
								<p class="mt-1 line-clamp-2 text-[11px] text-slate-500">
									{r.description}
								</p>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		</section>

		<!-- Role Detail & Permissions Matrix Card -->
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs" aria-labelledby="editor-h">
			{#if !role}
				<div class="p-12 text-center text-xs text-slate-400">
					Select a role to inspect and configure permissions.
				</div>
			{:else if isAdminRole}
				<!-- Admin Role Special View -->
				<div class="p-6">
					<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5">
						<div class="flex items-center gap-3">
							<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-purple-100 text-purple-700">
								<Icon icon={shieldCheck} class="h-5 w-5" />
							</div>
							<div>
								<div class="flex items-center gap-2">
									<h2 id="editor-h" class="text-base font-bold capitalize text-slate-900">{role.name}</h2>
									<span class="rounded-md bg-purple-50 px-2 py-0.5 text-[11px] font-bold text-purple-700 ring-1 ring-inset ring-purple-600/20">
										System Role
									</span>
								</div>
								<p class="text-xs text-slate-500 mt-0.5">Primary workspace administrator with full permissions</p>
							</div>
						</div>
					</div>

					<div class="mt-6 rounded-xl border border-purple-200 bg-purple-50/60 p-4 text-xs text-purple-900 leading-relaxed">
						<span class="font-bold">Full Tenant Access:</span> All catalog capabilities, financial records, client operations, and user administration scopes are unconditionally granted to this role. It cannot be altered or deleted.
					</div>

					{#if role.description}
						<div class="mt-4 rounded-xl border border-slate-200 bg-slate-50/50 p-4">
							<span class="text-xs font-semibold uppercase tracking-wider text-slate-500">Role Purpose:</span>
							<p class="mt-1 text-xs text-slate-700">{role.description}</p>
						</div>
					{/if}
				</div>
			{:else if isSuperAdminRole}
				<!-- Super Admin Platform View -->
				<div class="p-6">
					<div class="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center">
						<Icon icon={shieldCheck} class="mx-auto h-8 w-8 text-slate-400" />
						<h3 class="mt-2 text-sm font-bold text-slate-800">Platform Super Administrator</h3>
						<p class="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
							This is an internal root role governed by the platform console and cannot be managed within tenant workspaces.
						</p>
					</div>
				</div>
			{:else}
				<!-- Editable System or Custom Role View -->
				<div class="p-6">
					<!-- Role Title & Actions Toolbar -->
					<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5">
						<div>
							<div class="flex items-center gap-2">
								<h2 id="editor-h" class="text-base font-bold capitalize text-slate-900">{role.name}</h2>
								<span
									class="inline-flex rounded-md px-2 py-0.5 text-[11px] font-bold ring-1 ring-inset {role.is_system
										? 'bg-slate-100 text-slate-600 ring-slate-500/20'
										: 'bg-indigo-50 text-indigo-700 ring-indigo-500/20'}"
								>
									{role.is_system ? 'System Role' : 'Custom Role'}
								</span>
								<span class="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
									{grantedCount} / {totalCatalogCount} active scopes
								</span>
							</div>
							<p class="text-xs text-slate-500 mt-1">{role.description || 'Configured team permission profile.'}</p>
						</div>

						<div class="flex flex-wrap items-center gap-2">
							{#if role.is_system}
								<button
									type="button"
									disabled={resetBusy}
									aria-busy={resetBusy}
									onclick={resetRoleDefaults}
									class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60 transition-colors"
								>
									{#if resetBusy}
										<Spinner class="h-3.5 w-3.5 text-slate-600" />
									{:else}
										<Icon icon={refresh} class="h-3.5 w-3.5 text-slate-500" />
									{/if}
									Reset Defaults
								</button>
							{:else}
								<button
									type="button"
									onclick={() => {
										deleteErr = null;
										deleteOpen = true;
									}}
									class="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50/50 px-3 py-1.5 text-xs font-semibold text-red-700 shadow-2xs hover:bg-red-100/60 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none transition-colors"
								>
									<Icon icon={trashCanOutline} class="h-3.5 w-3.5" />
									Delete Role
								</button>
							{/if}
						</div>
					</div>

					<form
						class="mt-6 space-y-6"
						onsubmit={(e) => {
							e.preventDefault();
							saveRole();
						}}
					>
						<!-- Role Metadata Fields (For Custom Roles) -->
						{#if !role.is_system}
							<div class="grid gap-4 sm:grid-cols-2 rounded-xl border border-slate-100 bg-slate-50/50 p-4">
								<div>
									<label for="role-name" class="block text-xs font-semibold uppercase tracking-wider text-slate-600">
										Role Identifier Name *
									</label>
									<input
										id="role-name"
										type="text"
										bind:value={draftName}
										class="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
									/>
								</div>
								<div>
									<label for="role-desc" class="block text-xs font-semibold uppercase tracking-wider text-slate-600">
										Description
									</label>
									<input
										id="role-desc"
										type="text"
										bind:value={draftDesc}
										placeholder="e.g. Project manager with client billing access"
										class="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
									/>
								</div>
							</div>
						{/if}

						{#if !catalogOk}
							<div
								role="alert"
								class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800 shadow-2xs"
							>
								The permission catalog could not be loaded. Save is disabled to prevent accidental revocation.
							</div>
						{:else}
							<!-- Permissions Search & Category Matrix -->
							<div>
								<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-3">
									<div>
										<h3 class="text-xs font-bold uppercase tracking-wider text-slate-700">
											Permissions &amp; Scopes
										</h3>
										<p class="text-[11px] text-slate-400">Toggle individual permissions or apply group bulk actions.</p>
									</div>

									<!-- Quick Permission Search -->
									<div class="relative min-w-[220px]">
										<Icon icon={magnify} class="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
										<input
											type="text"
											bind:value={permSearch}
											placeholder="Search scopes..."
											class="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
										/>
									</div>
								</div>

								{#if filteredGroups.length === 0}
									<div class="rounded-xl border border-slate-200 p-8 text-center text-xs text-slate-400">
										No permissions match "{permSearch}".
									</div>
								{:else}
									<div class="space-y-4">
										{#each filteredGroups as g (g.group)}
											{@const allGranted = g.items.every((c) => draftGranted.has(`${c.action}.${c.resource}`))}
											{@const someGranted = g.items.some((c) => draftGranted.has(`${c.action}.${c.resource}`))}
											
											<div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
												<!-- Category Group Header -->
												<div class="flex items-center justify-between border-b border-slate-100 bg-slate-50/70 px-4 py-2.5">
													<div class="flex items-center gap-2">
														<Icon icon={g.icon} class="h-4 w-4 text-indigo-600" />
														<span class="text-xs font-bold text-slate-800">{g.group}</span>
														<span class="text-[10px] font-semibold text-slate-400">({g.items.length})</span>
													</div>

													{#if canEdit}
														<div class="flex items-center gap-2">
															<button
																type="button"
																onclick={() => grantGroup(g.items)}
																class="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
															>
																<Icon icon={checkAll} class="h-3.5 w-3.5" />
																Grant all
															</button>
															<span class="text-slate-300">|</span>
															<button
																type="button"
																onclick={() => revokeGroup(g.items)}
																class="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 hover:text-slate-700 transition-colors"
															>
																<Icon icon={closeCircleOutline} class="h-3.5 w-3.5" />
																Revoke all
															</button>
														</div>
													{/if}
												</div>

												<!-- Permissions Toggle Rows -->
												<ul class="divide-y divide-slate-100">
													{#each g.items as c (`${c.action}.${c.resource}`)}
														{@const key = `${c.action}.${c.resource}`}
														{@const granted = draftGranted.has(key)}
														<li class="flex items-center justify-between px-4 py-2.5 hover:bg-slate-50/60 transition-colors">
															<div class="min-w-0 pr-4">
																<p class="text-xs font-medium text-slate-800">{c.label}</p>
																<p class="font-mono text-[10px] text-slate-400">{c.action}:{c.resource}</p>
															</div>

															<label class="relative inline-flex items-center cursor-pointer">
																<input
																	type="checkbox"
																	class="peer sr-only"
																	disabled={!canEdit}
																	checked={granted}
																	onchange={() => togglePerm(c.action, c.resource)}
																	aria-label={`Toggle ${c.label}`}
																/>
																<span
																	aria-hidden="true"
																	class="relative inline-flex h-5 w-9 shrink-0 rounded-full bg-slate-300 transition-colors peer-checked:bg-indigo-600 peer-disabled:opacity-50 after:absolute after:top-0.5 after:left-0.5 after:h-4 after:w-4 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:after:translate-x-4"
																></span>
															</label>
														</li>
													{/each}
												</ul>
											</div>
										{/each}
									</div>
								{/if}
							</div>
						{/if}

						<!-- Save Action Button -->
						{#if canEdit}
							<div class="flex justify-end pt-4 border-t border-slate-100">
								<button
									type="submit"
									disabled={saveBusy || !canEdit || !catalogOk}
									aria-busy={saveBusy}
									class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60 transition-colors"
								>
									{#if saveBusy}
										<Spinner class="h-3.5 w-3.5 text-white" />
									{/if}
									Save Changes
								</button>
							</div>
						{/if}
					</form>
				</div>
			{/if}
		</section>
	</div>
</div>

<!-- Create New Custom Role Modal Dialog -->
<Dialog.Root bind:open={newOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs animate-fade-in" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 max-h-[85vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl bg-white p-6 shadow-2xl border border-slate-100 focus:outline-none animate-in"
		>
			<div class="flex items-center justify-between border-b border-slate-100 pb-4">
				<div class="flex items-center gap-2.5">
					<div class="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
						<Icon icon={plus} class="h-5 w-5" />
					</div>
					<div>
						<Dialog.Title class="text-sm font-bold text-slate-900">Create Custom Role</Dialog.Title>
						<Dialog.Description class="text-xs text-slate-500 mt-0.5">
							Define a custom role name and select authorized permissions.
						</Dialog.Description>
					</div>
				</div>
				<Dialog.Close
					type="button"
					aria-label="Close"
					class="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
				>
					<Icon icon={close} class="h-5 w-5" />
				</Dialog.Close>
			</div>

			{#if newErr}
				<div
					role="alert"
					class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-800"
				>
					{newErr}
				</div>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitNewRole();
				}}
			>
				<div>
					<label for="new-name" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
						Role Name *
					</label>
					<input
						id="new-name"
						type="text"
						bind:value={newName}
						required
						placeholder="e.g. Finance Specialist, Support Engineer"
						class="block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					/>
				</div>

				<div>
					<label for="new-desc" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
						Description
					</label>
					<input
						id="new-desc"
						type="text"
						bind:value={newDesc}
						placeholder="Brief summary of what this role handles"
						class="block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					/>
				</div>

				{#if catalogOk}
					<div class="pt-2">
						<div class="flex items-center justify-between mb-2">
							<p class="text-xs font-semibold uppercase tracking-wider text-slate-600">Permissions ({newGranted.size} selected)</p>
							<div class="relative w-44">
								<Icon icon={magnify} class="absolute left-2 top-2 h-3 w-3 text-slate-400" />
								<input
									type="text"
									bind:value={newPermSearch}
									placeholder="Filter..."
									class="w-full rounded-md border border-slate-200 bg-white py-1 pl-6 pr-2 text-[11px] placeholder-slate-400 shadow-2xs focus:border-indigo-500 focus:outline-none"
								/>
							</div>
						</div>

						<div class="max-h-60 space-y-3 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50/50 p-3">
							{#each groups as g (g.group)}
								{@const matchingItems = newPermSearch.trim()
									? g.items.filter((c) => c.label.toLowerCase().includes(newPermSearch.toLowerCase()) || g.group.toLowerCase().includes(newPermSearch.toLowerCase()))
									: g.items}

								{#if matchingItems.length > 0}
									<div class="rounded-lg border border-slate-200 bg-white p-2.5">
										<div class="flex items-center justify-between mb-2">
											<span class="text-[11px] font-bold uppercase tracking-wider text-slate-700">{g.group}</span>
											<div class="flex items-center gap-1.5 text-[10px]">
												<button
													type="button"
													onclick={() => grantNewGroup(matchingItems)}
													class="font-semibold text-indigo-600 hover:text-indigo-800"
												>
													All
												</button>
												<span class="text-slate-300">/</span>
												<button
													type="button"
													onclick={() => revokeNewGroup(matchingItems)}
													class="font-semibold text-slate-400 hover:text-slate-600"
												>
													None
												</button>
											</div>
										</div>

										<ul class="divide-y divide-slate-100">
											{#each matchingItems as c (`${c.action}.${c.resource}`)}
												{@const key = `${c.action}.${c.resource}`}
												<li class="flex items-center justify-between py-1.5">
													<span class="text-xs text-slate-700">{c.label}</span>
													<label class="relative inline-flex items-center cursor-pointer">
														<input
															type="checkbox"
															class="peer sr-only"
															checked={newGranted.has(key)}
															onchange={() => toggleNewPerm(c.action, c.resource)}
															aria-label={`Grant ${c.label}`}
														/>
														<span
															aria-hidden="true"
															class="relative inline-flex h-4 w-7 shrink-0 rounded-full bg-slate-300 transition-colors peer-checked:bg-indigo-600 after:absolute after:top-0.5 after:left-0.5 after:h-3 after:w-3 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:after:translate-x-3"
														></span>
													</label>
												</li>
											{/each}
										</ul>
									</div>
								{/if}
							{/each}
						</div>
					</div>
				{/if}

				<div class="mt-6 flex justify-end gap-2.5 pt-3 border-t border-slate-100">
					<Dialog.Close
						type="button"
						class="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={newBusy}
						aria-busy={newBusy}
						class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60 transition-colors"
					>
						{#if newBusy}
							<Spinner class="h-3.5 w-3.5 text-white" />
						{/if}
						Create Role
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Delete Role Confirmation Modal -->
<ConfirmDialog
	bind:open={deleteOpen}
	title="Delete Custom Role"
	description={role && !role.is_system
		? `Are you sure you want to delete the "${role.name}" role? Any users currently assigned to this role must be reassigned before deletion.`
		: ''}
	confirmLabel="Delete Role"
	destructive
	busy={deleteBusy}
	onconfirm={runDelete}
/>
