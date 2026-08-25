<script>
	import { invalidateAll } from '$app/navigation';
	import { ApiError } from '$lib/api/client.js';
	import * as tenantApi from '$lib/api/tenant.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDate, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = auth.token;
	const enumRoles = ['admin', 'manager', 'employee'];

	let canManageTeam = $derived(auth.can('manage', 'admin_users'));
	let activeAdminCount = $derived(
		data.users.items.filter((u) => u.role === 'admin' && u.is_active).length
	);

	let roleOptions = $derived(data.roles.filter((r) => r.name !== 'super_admin'));

	function currentRoleId(u) {
		if (u.role_id) return u.role_id;
		const sys = data.roles.find((r) => r.is_system && r.name === u.role);
		return sys?.id ?? '';
	}

	function isLastAdmin(u) {
		return u.role === 'admin' && u.is_active && activeAdminCount <= 1;
	}

	let inviteEmail = $state('');
	let inviteRole = $state('employee');
	let inviteBusy = $state(false);
	let inviteErr = $state(null);
	let inviteMsg = $state(null);

	async function sendInvite() {
		inviteBusy = true;
		inviteErr = null;
		inviteMsg = null;
		try {
			await tenantApi.createInvite(fetch, token, {
				email: inviteEmail,
				role: inviteRole
			});
			inviteMsg = `Invite sent to ${inviteEmail}.`;
			inviteEmail = '';
			await invalidateAll();
		} catch (e) {
			inviteErr = e instanceof ApiError ? e.message : 'Invite failed.';
		} finally {
			inviteBusy = false;
		}
	}

	let revokeTarget = $state(null);
	let revokeBusy = $state(false);

	async function revokeInvite() {
		if (!revokeTarget) return;
		revokeBusy = true;
		try {
			await tenantApi.deleteInvite(fetch, token, revokeTarget.id);
			revokeTarget = null;
			await invalidateAll();
		} catch (e) {
			inviteErr = e instanceof ApiError ? e.message : 'Revoke failed.';
		} finally {
			revokeBusy = false;
		}
	}

	let userErr = $state(null);

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

	async function reactivateUser(u) {
		userErr = null;
		try {
			await tenantApi.setUserActive(fetch, token, u.id, 'reactivate');
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Reactivation failed.';
		}
	}
</script>

<svelte:head><title>Team — ZenEngr</title></svelte:head>

<h1 class="text-2xl font-semibold text-slate-900">Team</h1>
<p class="mt-1 text-sm text-slate-500">{data.users.total} staff users</p>

{#if userErr}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{userErr}
	</p>
{/if}

<!-- Users table -->
<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	<div class="overflow-x-auto">
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
						<th scope="col" class="px-4 py-3"><span class="sr-only">Actions</span></th>{/if}
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-200">
				{#each data.users.items as u (u.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-4 py-3 text-sm font-medium text-slate-900">
							{u.full_name}
							{#if u.id === auth.user?.id}
								<span class="ml-1 text-xs text-slate-400">(you)</span>
							{/if}
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
						<td class="px-4 py-3"><StatusBadge status={u.is_active ? 'active' : 'inactive'} /></td>
						<td class="px-4 py-3 text-sm text-slate-600">{formatDate(u.created_at)}</td>
						{#if canManageTeam}
							<td class="px-4 py-3 text-right">
								{#if u.id !== auth.user?.id}
									{#if u.is_active}
										<button
											type="button"
											disabled={isLastAdmin(u)}
											title={isLastAdmin(u)
												? 'The last active admin cannot be deactivated'
												: undefined}
											onclick={() => (deactivateTarget = u)}
											class="text-sm font-medium text-red-600 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-50"
										>
											Deactivate
										</button>
									{:else}
										<button
											type="button"
											onclick={() => reactivateUser(u)}
											class="text-sm font-medium text-green-700 hover:text-green-600"
										>
											Reactivate
										</button>
									{/if}
								{/if}
							</td>
						{/if}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

{#if canManageTeam}
	<!-- Invite form -->
	<section
		class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="invite-h"
	>
		<h2 id="invite-h" class="text-base font-semibold text-slate-900">Invite user</h2>
		{#if inviteMsg}
			<p
				role="status"
				class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
			>
				{inviteMsg}
			</p>
		{/if}
		{#if inviteErr}
			<p
				role="alert"
				class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{inviteErr}
			</p>
		{/if}
		<form
			class="mt-4 flex flex-wrap items-end gap-3"
			onsubmit={(e) => {
				e.preventDefault();
				sendInvite();
			}}
		>
			<div>
				<label for="inv-email" class="block text-sm font-medium text-slate-700">Email</label>
				<input
					id="inv-email"
					type="email"
					bind:value={inviteEmail}
					required
					class="mt-1 block w-72 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="inv-role" class="block text-sm font-medium text-slate-700">Role</label>
				<select
					id="inv-role"
					bind:value={inviteRole}
					class="mt-1 block rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				>
					{#each enumRoles as r (r)}
						<option value={r}>{humanize(r)}</option>
					{/each}
				</select>
			</div>
			<button
				type="submit"
				disabled={inviteBusy}
				aria-busy={inviteBusy}
				class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if inviteBusy}<Spinner class="h-4 w-4 text-white" />{/if}
				Send invite
			</button>
		</form>
	</section>
{/if}

<!-- Invites list -->
<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="invites-h"
>
	<h2
		id="invites-h"
		class="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
	>
		Pending invites
	</h2>
	{#if data.invites.length === 0}
		<p class="px-6 py-8 text-sm text-slate-500">No invites yet.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="min-w-full divide-y divide-slate-200">
				<thead class="bg-slate-50">
					<tr>
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
							>Expires</th
						>
						{#if canManageTeam}<th scope="col" class="px-4 py-3"
								><span class="sr-only">Actions</span></th
							>{/if}
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200">
					{#each data.invites as invite (invite.id)}
						<tr>
							<td class="px-4 py-3 text-sm text-slate-900">{invite.email}</td>
							<td class="px-4 py-3 text-sm text-slate-600">{humanize(invite.role)}</td>
							<td class="px-4 py-3"><StatusBadge status={invite.status} /></td>
							<td class="px-4 py-3 text-sm text-slate-600">{formatDate(invite.expires_at)}</td>
							{#if canManageTeam}
								<td class="px-4 py-3 text-right">
									{#if invite.status === 'pending'}
										<button
											type="button"
											onclick={() => (revokeTarget = invite)}
											class="text-sm font-medium text-red-600 hover:text-red-500"
											aria-label={`Revoke invite for ${invite.email}`}
										>
											Revoke
										</button>
									{/if}
								</td>
							{/if}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>

<ConfirmDialog
	bind:open={
		() => revokeTarget !== null,
		(v) => {
			if (!v) revokeTarget = null;
		}
	}
	title="Revoke invite"
	description={revokeTarget ? `Revoke the pending invite for ${revokeTarget.email}?` : ''}
	confirmLabel="Revoke"
	destructive
	busy={revokeBusy}
	onconfirm={revokeInvite}
/>

<ConfirmDialog
	bind:open={
		() => deactivateTarget !== null,
		(v) => {
			if (!v) deactivateTarget = null;
		}
	}
	title="Deactivate user"
	description={deactivateTarget
		? `${deactivateTarget.full_name} will lose access until reactivated.`
		: ''}
	confirmLabel="Deactivate"
	destructive
	busy={deactivateBusy}
	onconfirm={deactivateUser}
/>
