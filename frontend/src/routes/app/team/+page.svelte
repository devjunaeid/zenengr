<script>
	import { invalidateAll } from '$app/navigation';
	import { Dialog } from 'bits-ui';
	import { ApiError, assetUrl } from '$lib/api/client.js';
	import * as tenantApi from '$lib/api/tenant.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, humanize } from '$lib/utils/format.js';

	let { data } = $props();

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

	/** @type {string} */
	const token = auth.token ?? '';

	let canManageTeam = $derived(auth.can('manage', 'admin_users'));
	let activeAdminCount = $derived(
		data.users.items.filter((u) => u.role === 'admin' && u.is_active).length
	);

	let roleOptions = $derived(data.roles.filter((r) => r.name !== 'super_admin'));

	/** @param {any} u */
	function currentRoleId(u) {
		if (u.role_id) return u.role_id;
		const sys = data.roles.find((r) => r.is_system && r.name === u.role);
		return sys?.id ?? '';
	}

	/** @param {any} u */
	function isLastAdmin(u) {
		return u.role === 'admin' && u.is_active && activeAdminCount <= 1;
	}

	// ── Add Employee Modal / Form ──────────────────────────────────────────────
	let showAddModal = $state(false);
	let addName = $state('');
	let addEmail = $state('');
	let addPassword = $state('');
	let addRoleId = $state('');
	let addBusy = $state(false);
	/** @type {string|null} */
	let addErr = $state(null);
	let showAddPassword = $state(false);

	function openAddModal() {
		addName = '';
		addEmail = '';
		addPassword = '';
		addRoleId = roleOptions.find((r) => r.name === 'employee')?.id ?? roleOptions[0]?.id ?? '';
		addErr = null;
		showAddModal = true;
	}

	function generatePassword() {
		const chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*';
		let pass = '';
		for (let i = 0; i < 12; i++) {
			pass += chars.charAt(Math.floor(Math.random() * chars.length));
		}
		addPassword = pass;
		showAddPassword = true;
	}

	async function createEmployee() {
		addBusy = true;
		addErr = null;
		try {
			await tenantApi.createUser(fetch, token, {
				full_name: addName.trim(),
				email: addEmail.trim(),
				password: addPassword,
				role_id: addRoleId || null
			});
			showAddModal = false;
			await invalidateAll();
		} catch (e) {
			addErr = e instanceof ApiError ? e.message : 'Failed to create employee.';
		} finally {
			addBusy = false;
		}
	}

	// ── Set / Reset Password Modal ────────────────────────────────────────────
	/** @type {any} */
	let passwordTarget = $state(null);
	let newPassword = $state('');
	let setPasswordBusy = $state(false);
	/** @type {string|null} */
	let setPasswordErr = $state(null);
	let showSetPassword = $state(false);

	/** @param {any} u */
	function openSetPasswordModal(u) {
		passwordTarget = u;
		newPassword = '';
		setPasswordErr = null;
	}

	function generateResetPassword() {
		const chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*';
		let pass = '';
		for (let i = 0; i < 12; i++) {
			pass += chars.charAt(Math.floor(Math.random() * chars.length));
		}
		newPassword = pass;
		showSetPassword = true;
	}

	async function submitSetPassword() {
		if (!passwordTarget) return;
		setPasswordBusy = true;
		setPasswordErr = null;
		try {
			await tenantApi.setUserPassword(fetch, token, passwordTarget.id, newPassword);
			passwordTarget = null;
			newPassword = '';
			await invalidateAll();
		} catch (e) {
			setPasswordErr = e instanceof ApiError ? e.message : 'Failed to set password.';
		} finally {
			setPasswordBusy = false;
		}
	}

	// ── Delete / Archive Employee ─────────────────────────────────────────────
	/** @type {any} */
	let deleteTarget = $state(null);
	let deleteBusy = $state(false);

	async function archiveEmployee() {
		if (!deleteTarget) return;
		deleteBusy = true;
		try {
			await tenantApi.deleteUser(fetch, token, deleteTarget.id);
			deleteTarget = null;
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Archive failed.';
		} finally {
			deleteBusy = false;
		}
	}

	// ── Role Changes & Deactivation ───────────────────────────────────────────
	/** @type {string|null} */
	let userErr = $state(null);

	/**
	 * @param {any} u
	 * @param {string} roleId
	 */
	async function changeRole(u, roleId) {
		if (roleId === currentRoleId(u)) return;
		userErr = null;
		try {
			await tenantApi.changeRole(fetch, token, u.id, roleId);
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Role change failed.';
			await invalidateAll();
		}
	}

	/** @type {any} */
	let deactivateTarget = $state(null);
	let deactivateBusy = $state(false);

	async function deactivateUser() {
		if (!deactivateTarget) return;
		deactivateBusy = true;
		try {
			await tenantApi.setUserActive(fetch, token, deactivateTarget.id, 'deactivate');
			deactivateTarget = null;
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Deactivation failed.';
		} finally {
			deactivateBusy = false;
		}
	}

	/** @param {any} u */
	async function reactivateUser(u) {
		userErr = null;
		try {
			await tenantApi.setUserActive(fetch, token, u.id, 'reactivate');
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Reactivation failed.';
		}
	}

	// ── Search & Filter State ──────────────────────────────────────────────────
	let searchQuery = $state('');
	let filterRole = $state('all');
	let filterStatus = $state('all');

	let filteredUsers = $derived(
		data.users.items.filter((u) => {
			if (searchQuery.trim()) {
				const q = searchQuery.toLowerCase().trim();
				const matchName = u.full_name?.toLowerCase().includes(q);
				const matchEmail = u.email?.toLowerCase().includes(q);
				if (!matchName && !matchEmail) return false;
			}
			if (filterRole !== 'all') {
				const uRoleId = currentRoleId(u);
				if (u.role !== filterRole && uRoleId !== filterRole) return false;
			}
			if (filterStatus === 'active' && !u.is_active) return false;
			if (filterStatus === 'inactive' && u.is_active) return false;
			return true;
		})
	);

	let isFiltered = $derived(
		Boolean(searchQuery.trim() || filterRole !== 'all' || filterStatus !== 'all')
	);

	function clearFilters() {
		searchQuery = '';
		filterRole = 'all';
		filterStatus = 'all';
	}
</script>

<svelte:head><title>Team — ZenEngr</title></svelte:head>

<div class="flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Team Management</h1>
		<p class="mt-1 text-sm text-slate-500">{data.users.total} team members</p>
	</div>
	{#if canManageTeam}
		<button
			type="button"
			onclick={openAddModal}
			class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
			</svg>
			Add Employee
		</button>
	{/if}
</div>

{#if userErr}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{userErr}
	</p>
{/if}

<!-- ── Search & Filter Controls ───────────────────────────────────────────── -->
<div
	class="mt-6 flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-3.5 shadow-2xs sm:flex-row sm:items-center sm:justify-between"
>
	<!-- Search Box -->
	<div class="relative min-w-[240px] flex-1">
		<div
			class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400"
		>
			<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
				/>
			</svg>
		</div>
		<input
			type="text"
			bind:value={searchQuery}
			placeholder="Search by name or email..."
			class="block w-full rounded-md border-slate-300 pr-8 pl-9 text-sm placeholder-slate-400 shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
		/>
		{#if searchQuery}
			<button
				type="button"
				onclick={() => (searchQuery = '')}
				class="absolute inset-y-0 right-0 flex items-center pr-2.5 text-slate-400 hover:text-slate-600"
				aria-label="Clear search"
			>
				<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		{/if}
	</div>

	<!-- Filter Selectors -->
	<div class="flex flex-wrap items-center gap-2.5">
		<!-- Role Filter -->
		<select
			bind:value={filterRole}
			class="rounded-md border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
			aria-label="Filter by role"
		>
			<option value="all">All Roles</option>
			{#each roleOptions as r (r.id)}
				<option value={r.name}>{r.name}</option>
			{/each}
		</select>

		<!-- Status Filter -->
		<select
			bind:value={filterStatus}
			class="rounded-md border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
			aria-label="Filter by status"
		>
			<option value="all">All Statuses</option>
			<option value="active">Active</option>
			<option value="inactive">Inactive / Revoked</option>
		</select>

		<!-- Clear Filters Button -->
		{#if isFiltered}
			<button
				type="button"
				onclick={clearFilters}
				class="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
			>
				<svg
					class="h-3.5 w-3.5 text-slate-400"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					stroke-width="2"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				</svg>
				Clear
			</button>
		{/if}
	</div>
</div>

<!-- Users mobile & tablet card view (< lg) -->
<div class="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm lg:hidden">
	{#if filteredUsers.length === 0}
		<div class="px-4 py-12 text-center">
			<p class="text-sm font-medium text-slate-900">No team members match your criteria</p>
			<p class="mt-1 text-xs text-slate-500">Try adjusting your search query or filters.</p>
			{#if isFiltered}
				<button
					type="button"
					onclick={clearFilters}
					class="mt-3 inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
				>
					Clear all filters
				</button>
			{/if}
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-3 bg-slate-50/60 p-3 sm:grid-cols-2">
			{#each filteredUsers as u (u.id)}
				<div
					class="flex flex-col justify-between space-y-3 rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs transition-shadow hover:shadow-xs"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="flex min-w-0 items-center gap-3">
							<div
								class="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-xs font-bold text-white shadow-2xs"
							>
								<span class="select-none">{getInitials(u.full_name)}</span>
								{#if u.avatar_url}
									<img
										src={assetUrl(u.avatar_url)}
										alt=""
										class="absolute inset-0 h-full w-full object-cover"
										onerror={(e) => {
											e.currentTarget.style.display = 'none';
										}}
									/>
								{/if}
							</div>
							<div class="min-w-0">
								<div class="flex items-center gap-2">
									<span class="truncate text-sm font-semibold text-slate-900">{u.full_name}</span>
									{#if u.id === auth.user?.id}
										<span
											class="rounded bg-indigo-50 px-1.5 py-0.5 text-xs font-semibold text-indigo-700"
											>You</span
										>
									{/if}
								</div>
								<p class="mt-0.5 truncate text-xs text-slate-500">{u.email}</p>
							</div>
						</div>
						<StatusBadge status={u.is_active ? 'active' : 'inactive'} />
					</div>

					<div
						class="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 p-2.5 text-xs"
					>
						<div class="flex items-center gap-2">
							<span class="text-slate-400">Role:</span>
							{#if canManageTeam}
								<select
									id="m-role-{u.id}"
									value={currentRoleId(u)}
									disabled={isLastAdmin(u)}
									title={isLastAdmin(u) ? 'The last active admin cannot be demoted' : undefined}
									onchange={(e) => changeRole(u, e.currentTarget.value)}
									class="rounded border-slate-300 py-1 pr-7 pl-2 text-xs font-medium shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 disabled:opacity-60"
								>
									{#each roleOptions as r (r.id)}
										<option value={r.id}>{r.name}</option>
									{/each}
								</select>
							{:else}
								<span class="font-medium text-slate-700">{humanize(u.role)}</span>
							{/if}
						</div>
						<div>
							<span class="text-slate-400">Joined:</span>
							<span class="ml-1 text-slate-600">{formatDate(u.created_at)}</span>
						</div>
					</div>

					{#if canManageTeam && u.id !== auth.user?.id}
						<div class="flex items-center justify-end gap-2 pt-1">
							<button
								type="button"
								onclick={() => openSetPasswordModal(u)}
								class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50"
							>
								Password
							</button>

							{#if u.is_active}
								<button
									type="button"
									disabled={isLastAdmin(u)}
									onclick={() => (deactivateTarget = u)}
									class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-amber-700 shadow-2xs hover:bg-amber-50 disabled:opacity-40"
								>
									Revoke
								</button>
							{:else}
								<button
									type="button"
									onclick={() => reactivateUser(u)}
									class="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-2.5 py-1.5 text-xs font-semibold text-emerald-700 shadow-2xs hover:bg-emerald-100"
								>
									Restore
								</button>
							{/if}

							<button
								type="button"
								disabled={isLastAdmin(u)}
								onclick={() => (deleteTarget = u)}
								class="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-rose-700 shadow-2xs hover:bg-rose-50 disabled:opacity-40"
							>
								Archive
							</button>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Users desktop table (>= lg) -->
<div
	class="mt-4 hidden overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm lg:block"
>
	<div class="relative overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-200">
			<thead class="bg-slate-50">
				<tr>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Name</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Email</th
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
						>Joined</th
					>
					{#if canManageTeam}
						<th
							scope="col"
							class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
							>Actions</th
						>{/if}
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-200">
				{#if filteredUsers.length === 0}
					<tr>
						<td colspan="6" class="px-4 py-12 text-center">
							<p class="text-sm font-medium text-slate-900">No team members match your criteria</p>
							<p class="mt-1 text-xs text-slate-500">Try adjusting your search query or filters.</p>
							{#if isFiltered}
								<button
									type="button"
									onclick={clearFilters}
									class="mt-3 inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
								>
									Clear all filters
								</button>
							{/if}
						</td>
					</tr>
				{:else}
					{#each filteredUsers as u (u.id)}
						<tr class="transition-colors hover:bg-slate-50">
							<td class="px-4 py-3 text-sm font-medium text-slate-900">
								<div class="flex items-center gap-3">
									<div
										class="relative flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 text-xs font-bold text-white shadow-2xs"
									>
										<span class="select-none">{getInitials(u.full_name)}</span>
										{#if u.avatar_url}
											<img
												src={assetUrl(u.avatar_url)}
												alt=""
												class="absolute inset-0 h-full w-full object-cover"
												onerror={(e) => {
													e.currentTarget.style.display = 'none';
												}}
											/>
										{/if}
									</div>
									<div class="min-w-0">
										<span class="font-semibold text-slate-900">{u.full_name}</span>
										{#if u.id === auth.user?.id}
											<span
												class="ml-1.5 rounded bg-indigo-50 px-1.5 py-0.5 text-xs font-semibold text-indigo-700"
												>You</span
											>
										{/if}
									</div>
								</div>
							</td>
							<td class="px-4 py-3 text-sm text-slate-600">{u.email}</td>
							<td class="px-4 py-3">
								{#if canManageTeam}
									<label class="sr-only" for="role-{u.id}">Role for {u.full_name}</label>
									<select
										id="role-{u.id}"
										value={currentRoleId(u)}
										disabled={isLastAdmin(u)}
										title={isLastAdmin(u) ? 'The last active admin cannot be demoted' : undefined}
										onchange={(e) => changeRole(u, e.currentTarget.value)}
										class="block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
									>
										{#each roleOptions as r (r.id)}
											<option value={r.id}>{r.name}</option>
										{/each}
									</select>
								{:else}
									<span class="text-sm text-slate-600">{humanize(u.role)}</span>
								{/if}
							</td>
							<td class="px-4 py-3"><StatusBadge status={u.is_active ? 'active' : 'inactive'} /></td
							>
							<td class="px-4 py-3 text-sm text-slate-600">{formatDate(u.created_at)}</td>
							{#if canManageTeam}
								<td class="px-4 py-3 text-right">
									{#if u.id !== auth.user?.id}
										<div class="inline-flex items-center justify-end gap-1.5">
											<!-- Set Password Button -->
											<button
												type="button"
												onclick={() => openSetPasswordModal(u)}
												class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-2xs transition-all hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
												title="Set New Password"
												aria-label={`Set password for ${u.full_name}`}
											>
												<svg
													class="h-4 w-4"
													fill="none"
													viewBox="0 0 24 24"
													stroke="currentColor"
													stroke-width="2"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
													/>
												</svg>
											</button>

											<!-- Revoke / Restore Access Button -->
											{#if u.is_active}
												<button
													type="button"
													disabled={isLastAdmin(u)}
													title={isLastAdmin(u)
														? 'The last active admin cannot be deactivated'
														: 'Revoke Access (Deactivate)'}
													onclick={() => (deactivateTarget = u)}
													class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-2xs transition-all hover:border-amber-200 hover:bg-amber-50 hover:text-amber-600 focus:ring-2 focus:ring-amber-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-40"
													aria-label={`Revoke access for ${u.full_name}`}
												>
													<svg
														class="h-4 w-4"
														fill="none"
														viewBox="0 0 24 24"
														stroke="currentColor"
														stroke-width="2"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
														/>
													</svg>
												</button>
											{:else}
												<button
													type="button"
													onclick={() => reactivateUser(u)}
													class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700 shadow-2xs transition-all hover:border-emerald-300 hover:bg-emerald-100 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
													title="Restore Access (Reactivate)"
													aria-label={`Restore access for ${u.full_name}`}
												>
													<svg
														class="h-4 w-4"
														fill="none"
														viewBox="0 0 24 24"
														stroke="currentColor"
														stroke-width="2"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
														/>
													</svg>
												</button>
											{/if}

											<!-- Archive / Delete Button -->
											<button
												type="button"
												disabled={isLastAdmin(u)}
												title={isLastAdmin(u)
													? 'The last active admin cannot be deleted'
													: 'Archive Employee'}
												onclick={() => (deleteTarget = u)}
												class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-2xs transition-all hover:border-red-200 hover:bg-red-50 hover:text-red-600 focus:ring-2 focus:ring-red-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-40"
												aria-label={`Archive ${u.full_name}`}
											>
												<svg
													class="h-4 w-4"
													fill="none"
													viewBox="0 0 24 24"
													stroke="currentColor"
													stroke-width="2"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
													/>
												</svg>
											</button>
										</div>
									{/if}
								</td>
							{/if}
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
</div>

<!-- ── Add Employee Modal ─────────────────────────────────────────────────── -->
<Dialog.Root bind:open={showAddModal}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 max-h-[calc(100vh-2rem)] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg bg-white p-4 shadow-xl focus:outline-none sm:max-h-[85vh] sm:p-6"
		>
			<div class="flex items-center justify-between border-b border-slate-100 pb-3">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Add New Employee</Dialog.Title>
				<Dialog.Close
					aria-label="Close modal"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="sr-only">
				Create a new employee account with a role and initial password.
			</Dialog.Description>

			{#if addErr}
				<p class="mt-3 rounded-md bg-red-50 p-2.5 text-sm text-red-700">{addErr}</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					createEmployee();
				}}
			>
				<div>
					<label for="add-name" class="block text-sm font-medium text-slate-700">Full Name</label>
					<input
						id="add-name"
						type="text"
						bind:value={addName}
						placeholder="Jane Doe"
						required
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div>
					<label for="add-email" class="block text-sm font-medium text-slate-700"
						>Email Address</label
					>
					<input
						id="add-email"
						type="email"
						bind:value={addEmail}
						placeholder="jane@company.com"
						required
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div>
					<label for="add-role" class="block text-sm font-medium text-slate-700">Role</label>
					<select
						id="add-role"
						bind:value={addRoleId}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					>
						{#each roleOptions as r (r.id)}
							<option value={r.id}>{r.name}</option>
						{/each}
					</select>
				</div>

				<div>
					<div class="flex items-center justify-between">
						<label for="add-password" class="block text-sm font-medium text-slate-700"
							>Password</label
						>
						<button
							type="button"
							onclick={generatePassword}
							class="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
						>
							Auto-generate
						</button>
					</div>
					<div class="relative mt-1">
						<input
							id="add-password"
							type={showAddPassword ? 'text' : 'password'}
							bind:value={addPassword}
							placeholder="Minimum 8 characters"
							required
							minlength="8"
							class="block w-full rounded-md border-slate-300 pr-10 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
						<button
							type="button"
							onclick={() => (showAddPassword = !showAddPassword)}
							class="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600"
						>
							<span class="text-xs">{showAddPassword ? 'Hide' : 'Show'}</span>
						</button>
					</div>
				</div>

				<div class="mt-6 flex items-center justify-end gap-3 pt-2">
					<button
						type="button"
						onclick={() => (showAddModal = false)}
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
					>
						Cancel
					</button>
					<button
						type="submit"
						disabled={addBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
					>
						{#if addBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Create Employee
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- ── Set Password Modal ─────────────────────────────────────────────────── -->
<Dialog.Root
	bind:open={
		() => passwordTarget !== null,
		(v) => {
			if (!v) passwordTarget = null;
		}
	}
>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 max-h-[calc(100vh-2rem)] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg bg-white p-4 shadow-xl focus:outline-none sm:max-h-[85vh] sm:p-6"
		>
			<div class="flex items-center justify-between border-b border-slate-100 pb-3">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Set Password</Dialog.Title>
				<Dialog.Close
					aria-label="Close modal"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>

			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Setting new password for <span class="font-semibold text-slate-900"
					>{passwordTarget.full_name}</span
				>
				({passwordTarget.email}).
			</Dialog.Description>

			{#if setPasswordErr}
				<p class="mt-3 rounded-md bg-red-50 p-2.5 text-sm text-red-700">{setPasswordErr}</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitSetPassword();
				}}
			>
				<div>
					<div class="flex items-center justify-between">
						<label for="new-pass" class="block text-sm font-medium text-slate-700"
							>New Password</label
						>
						<button
							type="button"
							onclick={generateResetPassword}
							class="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
						>
							Auto-generate
						</button>
					</div>
					<div class="relative mt-1">
						<input
							id="new-pass"
							type={showSetPassword ? 'text' : 'password'}
							bind:value={newPassword}
							placeholder="Enter new password"
							required
							minlength="8"
							class="block w-full rounded-md border-slate-300 pr-10 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
						<button
							type="button"
							onclick={() => (showSetPassword = !showSetPassword)}
							class="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600"
						>
							<span class="text-xs">{showSetPassword ? 'Hide' : 'Show'}</span>
						</button>
					</div>
				</div>

				<div class="mt-6 flex items-center justify-end gap-3 pt-2">
					<button
						type="button"
						onclick={() => (passwordTarget = null)}
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
					>
						Cancel
					</button>
					<button
						type="submit"
						disabled={setPasswordBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
					>
						{#if setPasswordBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Update Password
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- ── Deactivate / Revoke Confirmation Dialog ────────────────────────────── -->
<ConfirmDialog
	bind:open={
		() => deactivateTarget !== null,
		(v) => {
			if (!v) deactivateTarget = null;
		}
	}
	title="Revoke Access"
	description={deactivateTarget
		? `Revoke access for ${deactivateTarget.full_name}? They will immediately be logged out and unable to access the system.`
		: ''}
	confirmLabel="Revoke Access"
	destructive
	busy={deactivateBusy}
	onconfirm={deactivateUser}
/>

<!-- ── Archive Employee Confirmation Dialog ────────────────────────────────── -->
<ConfirmDialog
	bind:open={
		() => deleteTarget !== null,
		(v) => {
			if (!v) deleteTarget = null;
		}
	}
	title="Archive Employee"
	description={deleteTarget
		? `Archive and remove ${deleteTarget.full_name} (${deleteTarget.email})? Their user account will be removed from the team roster.`
		: ''}
	confirmLabel="Archive Employee"
	destructive
	busy={deleteBusy}
	onconfirm={archiveEmployee}
/>
