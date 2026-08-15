<script>
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Icon from '@iconify/svelte';
	import { ApiError } from '$lib/api/client.js';
	import * as clientApi from '$lib/api/clients.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import LedgerTable from '$lib/components/LedgerTable.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import {
		auditActionLabel,
		auditGroup,
		formatClientActivityDetails,
		groupIcon
	} from '$lib/utils/audit.js';
	import { Dialog } from 'bits-ui';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatAddress } from '$lib/utils/address.js';
	import { formatDateTime, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	let canManage = $derived(auth.can('manage', 'clients'));
	let isEmployee = $derived(auth.user?.role === 'employee');

	// Client-user management (manage/clients only)
	/** @type {string|null} */
	let userErr = $state(null);
	/** @type {string|null} */
	let userMsg = $state(null);

	// Change password dialog
	/** @type {any|null} */
	let passwordUser = $state(null);
	let newPassword = $state('');
	let confirmPassword = $state('');
	let passwordBusy = $state(false);

	async function changePassword() {
		if (!passwordUser) return;
		passwordBusy = true;
		userErr = null;
		try {
			await clientApi.resetClientUserPassword(fetch, token, passwordUser.id, {
				password: newPassword
			});
			userMsg = `Password updated for ${passwordUser.email}.`;
			passwordUser = null;
			newPassword = '';
			confirmPassword = '';
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Password change failed.';
		} finally {
			passwordBusy = false;
		}
	}

	/** @type {any|null} */
	let revokeTarget = $state(null);
	let revokeBusy = $state(false);

	async function revokeAccess() {
		if (!revokeTarget) return;
		revokeBusy = true;
		userErr = null;
		try {
			await clientApi.deactivateClientUser(fetch, token, revokeTarget.id);
			userMsg = `Access revoked for ${revokeTarget.email}.`;
			revokeTarget = null;
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Revoke failed.';
		} finally {
			revokeBusy = false;
		}
	}

	/** @param {any} u */
	async function restoreAccess(u) {
		userErr = null;
		userMsg = null;
		try {
			await clientApi.reactivateClientUser(fetch, token, u.id);
			userMsg = `Access restored for ${u.email}.`;
			await invalidateAll();
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Restore failed.';
		}
	}

	// Archive / unarchive confirmation
	/** @type {null | 'archive' | 'unarchive'} */
	let archiveAction = $state(null);
	let archiveBusy = $state(false);
	/** @type {string|null} */
	let actionErr = $state(null);

	async function runArchiveAction() {
		if (!archiveAction) return;
		archiveBusy = true;
		actionErr = null;
		try {
			if (archiveAction === 'archive') {
				await clientApi.archiveClient(fetch, token, data.client.id);
			} else {
				await clientApi.unarchiveClient(fetch, token, data.client.id);
			}
			archiveAction = null;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Action failed.';
		} finally {
			archiveBusy = false;
		}
	}

	// Add note form
	let noteBody = $state('');
	let noteBusy = $state(false);
	/** @type {string|null} */
	let noteErr = $state(null);

	async function addNote() {
		if (!noteBody.trim()) return;
		noteBusy = true;
		noteErr = null;
		try {
			await clientApi.addNote(fetch, token, data.client.id, { body: noteBody.trim() });
			noteBody = '';
			await invalidateAll();
		} catch (e) {
			noteErr = e instanceof ApiError ? e.message : 'Add note failed.';
		} finally {
			noteBusy = false;
		}
	}

	// Pagination helpers — preserve other params when changing page.
	/** @param {number} p */
	function gotoNotesPage(p) {
		const params = new SvelteURLSearchParams(page.url.searchParams);
		if (p > 1) params.set('notes_page', String(p));
		else params.delete('notes_page');
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL on the same page
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}

	/** @param {number} p */
	function gotoActivityPage(p) {
		const params = new SvelteURLSearchParams(page.url.searchParams);
		if (p > 1) params.set('activity_page', String(p));
		else params.delete('activity_page');
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL on the same page
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}

	/** @param {string|number|null|undefined} n */
	function fmtNumber(n) {
		if (n == null || n === '') return '—';
		const num = typeof n === 'string' ? Number(n) : n;
		if (Number.isNaN(num)) return '—';
		return new Intl.NumberFormat(undefined).format(num);
	}
</script>

<svelte:head><title>{data.client.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/clients')} class="hover:text-indigo-600">Clients</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">{data.client.name}</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div class="flex items-center gap-3">
		<h1 class="text-2xl font-semibold text-slate-900">{data.client.name}</h1>
		<StatusBadge status={data.client.status} />
	</div>
	{#if canManage}
		<div class="flex items-center gap-2">
			<a
				href={resolve('/app/clients/[id]/edit', { id: data.client.id })}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Edit
			</a>
			{#if data.client.status === 'active'}
				<button
					type="button"
					onclick={() => (archiveAction = 'archive')}
					class="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
				>
					Archive
				</button>
			{:else}
				<button
					type="button"
					onclick={() => (archiveAction = 'unarchive')}
					class="rounded-md border border-green-300 bg-white px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-50 focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:outline-none"
				>
					Unarchive
				</button>
			{/if}
		</div>
	{/if}
</div>

{#if isEmployee}
	<p
		role="status"
		class="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
	>
		View only — contact an admin to make changes.
	</p>
{/if}

{#if actionErr}
	<p
		role="alert"
		class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{actionErr}
	</p>
{/if}

<div class="mt-6 grid gap-6 lg:grid-cols-3">
	<!-- Left: profile + contacts -->
	<div class="space-y-6 lg:col-span-2">
		<section
			class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
			aria-labelledby="profile-h"
		>
			<h2 id="profile-h" class="text-base font-semibold text-slate-900">Profile</h2>
			<dl class="mt-4 grid gap-4 sm:grid-cols-2">
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Name</dt>
					<dd class="mt-1 text-sm text-slate-900">{data.client.name}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Type</dt>
					<dd class="mt-1 text-sm text-slate-900">{humanize(data.client.client_type)}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Email</dt>
					<dd class="mt-1 text-sm text-slate-900">{data.client.email ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Phone</dt>
					<dd class="mt-1 text-sm text-slate-900">{data.client.phone ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Tax ID</dt>
					<dd class="mt-1 font-mono text-sm text-slate-900">{data.client.tax_id ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Status</dt>
					<dd class="mt-1"><StatusBadge status={data.client.status} /></dd>
				</div>
				<div class="sm:col-span-2">
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">
						Billing address
					</dt>
					<dd class="mt-1">
						{#if formatAddress(data.client.billing_address)}
							<address class="text-sm whitespace-pre-line text-slate-900 not-italic">
								{formatAddress(data.client.billing_address)}
							</address>
						{:else}
							<span class="text-sm text-slate-500">—</span>
						{/if}
					</dd>
				</div>
				<div class="sm:col-span-2">
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Tags</dt>
					<dd class="mt-1">
						{#if data.client.tags.length}
							<div class="flex flex-wrap gap-1">
								{#each data.client.tags as t (t)}
									<span
										class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-300 ring-inset"
									>
										{t}
									</span>
								{/each}
							</div>
						{:else}
							<span class="text-sm text-slate-500">—</span>
						{/if}
					</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Created</dt>
					<dd class="mt-1 text-sm text-slate-900">{formatDateTime(data.client.created_at)}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Updated</dt>
					<dd class="mt-1 text-sm text-slate-900">{formatDateTime(data.client.updated_at)}</dd>
				</div>
			</dl>
		</section>

		<section
			class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
			aria-labelledby="fin-h"
		>
			<h2 id="fin-h" class="text-base font-semibold text-slate-900">Financials</h2>
			<dl class="mt-4 grid gap-4 sm:grid-cols-3">
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">
						Active projects
					</dt>
					<dd class="mt-1 text-2xl font-semibold text-slate-900">
						{fmtNumber(data.client.active_projects)}
					</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Total invoiced</dt>
					<dd class="mt-1 text-2xl font-semibold text-slate-900">
						{fmtNumber(data.client.total_invoiced)}
					</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Outstanding</dt>
					<dd class="mt-1 text-2xl font-semibold text-slate-900">
						{fmtNumber(data.client.total_outstanding)}
					</dd>
				</div>
			</dl>
		</section>

		<section
			class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
			aria-labelledby="contacts-h"
		>
			<div class="flex flex-wrap items-center justify-between gap-3">
				<h2 id="contacts-h" class="text-base font-semibold text-slate-900">Contacts</h2>
			</div>

			{#if userMsg}
				<p
					role="status"
					class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
				>
					{userMsg}
				</p>
			{/if}
			{#if userErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{userErr}
				</p>
			{/if}

			{#if data.client.client_users.length === 0}
				<p class="mt-3 text-sm text-slate-500">No client users yet.</p>
			{:else}
				<ul class="mt-3 divide-y divide-slate-200">
					{#each data.client.client_users as u (u.id)}
						<li class="flex flex-wrap items-center justify-between gap-2 py-3">
							<div class="min-w-0">
								<p class="text-sm font-medium text-slate-900">
									{u.full_name ?? u.email}
								</p>
								<p class="text-xs text-slate-500">{u.email}</p>
							</div>
							<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
								<div class="flex flex-wrap items-center gap-2">
									{#if u.is_primary_billing_contact}
										<span
											class="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800 ring-1 ring-indigo-600/20 ring-inset"
										>
											Primary billing contact
										</span>
									{/if}
									<span
										class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {u.is_active
											? 'bg-green-100 text-green-800 ring-green-600/20'
											: 'bg-slate-200 text-slate-700 ring-slate-500/20'}"
									>
										{u.is_active ? 'Active' : 'Inactive'}
									</span>
								</div>
								{#if canManage}
									<div class="flex flex-wrap items-center gap-3">
										<button
											type="button"
											onclick={() => {
												userErr = null;
												userMsg = null;
												newPassword = '';
												confirmPassword = '';
												passwordUser = u;
											}}
											class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
											aria-label={`Change password for ${u.email}`}
										>
											Change password
										</button>
										{#if u.is_active}
											<button
												type="button"
												onclick={() => {
													userErr = null;
													revokeTarget = u;
												}}
												class="text-sm font-medium text-red-600 hover:text-red-500"
												aria-label={`Revoke access for ${u.email}`}
											>
												Revoke access
											</button>
										{:else}
											<button
												type="button"
												onclick={() => restoreAccess(u)}
												class="text-sm font-medium text-green-700 hover:text-green-600"
												aria-label={`Restore access for ${u.email}`}
											>
												Restore access
											</button>
										{/if}
									</div>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	</div>

	<!-- Right: notes + activity -->
	<div class="space-y-6">
		<section
			class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
			aria-labelledby="notes-h"
		>
			<h2 id="notes-h" class="text-base font-semibold text-slate-900">Notes</h2>

			{#if canManage}
				{#if noteErr}
					<p
						role="alert"
						class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
					>
						{noteErr}
					</p>
				{/if}
				<form
					class="mt-3"
					onsubmit={(e) => {
						e.preventDefault();
						addNote();
					}}
				>
					<label for="note-body" class="sr-only">New note</label>
					<textarea
						id="note-body"
						bind:value={noteBody}
						rows="3"
						placeholder="Add an internal note..."
						class="block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					></textarea>
					<div class="mt-2 flex justify-end">
						<button
							type="submit"
							disabled={noteBusy || !noteBody.trim()}
							aria-busy={noteBusy}
							class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
						>
							{#if noteBusy}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
							Add note
						</button>
					</div>
				</form>
			{/if}

			{#if data.notes.items.length === 0}
				<p class="mt-4 text-sm text-slate-500">No notes yet.</p>
			{:else}
				<ul class="mt-4 divide-y divide-slate-200">
					{#each data.notes.items as n (n.id)}
						<li class="py-3">
							<p class="text-sm whitespace-pre-wrap text-slate-800">{n.body}</p>
							<p class="mt-1 text-xs text-slate-500">
								{formatDateTime(n.created_at)}
								{#if n.author_id || n.author_name}
									· {n.author_name ?? 'Unknown'}
								{/if}
							</p>
						</li>
					{/each}
				</ul>
				<Pagination
					page={data.notes.page}
					pageSize={data.notes.page_size}
					total={data.notes.total}
					onpage={gotoNotesPage}
				/>
			{/if}
		</section>

		<section
			class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
			aria-labelledby="activity-h"
		>
			<h2 id="activity-h" class="text-base font-semibold text-slate-900">Activity</h2>
			{#if data.activity.items.length === 0}
				<p class="mt-4 text-sm text-slate-500">No activity recorded.</p>
			{:else}
				<ol class="mt-4 space-y-3">
					{#each data.activity.items as a (a.id)}
						{@const rows = formatClientActivityDetails(a.details)}
						<li class="flex gap-3 text-sm">
							<span
								class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500"
							>
								<Icon icon={groupIcon(auditGroup(a.action))} class="h-4 w-4" />
							</span>
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
									<span class="text-sm font-medium text-slate-900">
										{auditActionLabel(a.action)}
									</span>
									<span class="text-xs text-slate-500">
										{formatDateTime(a.created_at)}
									</span>
								</div>
								<div
									class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500"
								>
									<span
										class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-slate-600"
									>
										{a.actor_name || (a.actor_type ? humanize(a.actor_type) : 'System')}
									</span>
									<span>{a.entity_label || (a.entity_type ? humanize(a.entity_type) : '—')}</span>
								</div>
								{#if rows.length > 0}
									<details class="mt-1">
										<summary
											class="cursor-pointer text-xs font-medium text-indigo-600 select-none hover:text-indigo-500"
										>
											Details
										</summary>
										<dl class="mt-2 space-y-1 rounded-md bg-slate-50 px-3 py-2">
											{#each rows as row (row.label)}
												<div class="flex gap-2 text-xs">
													<dt class="w-32 shrink-0 text-slate-500">{row.label}</dt>
													<dd class="min-w-0 break-words text-slate-700">{row.value}</dd>
												</div>
											{/each}
										</dl>
									</details>
								{/if}
							</div>
						</li>
					{/each}
				</ol>
				<Pagination
					page={data.activity.page}
					pageSize={data.activity.page_size}
					total={data.activity.total}
					onpage={gotoActivityPage}
				/>
			{/if}
		</section>
	</div>
</div>

<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="ledger-h"
>
	<div
		class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-4"
	>
		<h2 id="ledger-h" class="text-base font-semibold text-slate-900">Ledger</h2>
		{#if data.ledger}
			<p class="text-sm text-slate-600">
				Advance balance:
				<span
					class="font-semibold {Number(data.ledger.advance_balance) > 0
						? 'text-green-600'
						: 'text-slate-900'}"
				>
					{fmtPrice(data.ledger.advance_balance)}
				</span>
			</p>
		{/if}
	</div>
	{#if data.ledger}
		<LedgerTable entries={data.ledger.entries} />
	{:else}
		<p class="px-6 py-8 text-sm text-slate-500">Ledger unavailable.</p>
	{/if}
</section>

<ConfirmDialog
	bind:open={
		() => archiveAction !== null,
		(v) => {
			if (!v) archiveAction = null;
		}
	}
	title={archiveAction === 'archive' ? 'Archive client' : 'Unarchive client'}
	description={archiveAction === 'archive'
		? `Archive ${data.client.name}? It will no longer appear in default lists.`
		: `Unarchive ${data.client.name}? It will become active again.`}
	confirmLabel={archiveAction === 'archive' ? 'Archive' : 'Unarchive'}
	destructive={archiveAction === 'archive'}
	busy={archiveBusy}
	onconfirm={runArchiveAction}
/>

<!-- Change password dialog -->
<Dialog.Root
	bind:open={
		() => passwordUser !== null,
		(v) => {
			if (!v) {
				passwordUser = null;
				userErr = null;
			}
		}
	}
>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold text-slate-900">Change password</Dialog.Title>
			{#if passwordUser}
				<Dialog.Description class="mt-2 text-sm text-slate-600">
					Set a new password for {passwordUser.email}. They will use it to sign in to the client
					portal.
				</Dialog.Description>
			{/if}

			{#if userErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{userErr}
				</p>
			{/if}

			<form
				class="mt-4"
				onsubmit={(e) => {
					e.preventDefault();
					changePassword();
				}}
			>
				<div>
					<label for="pw-new" class="block text-sm font-medium text-slate-700">New password</label>
					<input
						id="pw-new"
						type="password"
						bind:value={newPassword}
						required
						minlength="10"
						autocomplete="new-password"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div class="mt-4">
					<label for="pw-confirm" class="block text-sm font-medium text-slate-700"
						>Confirm password</label
					>
					<input
						id="pw-confirm"
						type="password"
						bind:value={confirmPassword}
						required
						minlength="10"
						autocomplete="new-password"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<p class="mt-1 text-xs text-slate-500">Password must be at least 10 characters.</p>
				{#if newPassword && confirmPassword && newPassword !== confirmPassword}
					<p role="alert" class="mt-2 text-xs text-red-600">Passwords do not match.</p>
				{/if}
				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						onclick={() => {
							userErr = null;
							passwordUser = null;
						}}
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={passwordBusy || !newPassword || newPassword !== confirmPassword}
						aria-busy={passwordBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if passwordBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Update password
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<ConfirmDialog
	bind:open={
		() => revokeTarget !== null,
		(v) => {
			if (!v) revokeTarget = null;
		}
	}
	title="Revoke access"
	description={revokeTarget
		? `Revoke portal access for ${revokeTarget.email}? They will no longer be able to sign in to the client portal.`
		: ''}
	confirmLabel="Revoke access"
	destructive
	busy={revokeBusy}
	onconfirm={revokeAccess}
/>
