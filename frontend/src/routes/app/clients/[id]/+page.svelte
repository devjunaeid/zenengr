<script>
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { ApiError } from '$lib/api/client.js';
	import * as clientApi from '$lib/api/clients.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import LedgerTable from '$lib/components/LedgerTable.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { Dialog } from 'bits-ui';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatAddress } from '$lib/utils/address.js';
	import { formatDateTime, fmtPrice, humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	let canManage = $derived(auth.can('manage', 'clients'));
	let isEmployee = $derived(auth.user?.role === 'employee');

	// Client-user invite dialog
	let inviteOpen = $state(false);
	let inviteEmail = $state('');
	let inviteBusy = $state(false);
	/** @type {string|null} */
	let inviteErr = $state(null);
	/** @type {string|null} */
	let inviteMsg = $state(null);

	async function sendInvite() {
		inviteBusy = true;
		inviteErr = null;
		inviteMsg = null;
		try {
			await clientApi.createClientInvite(fetch, token, data.client.id, {
				email: inviteEmail.trim()
			});
			inviteMsg = `Invite sent to ${inviteEmail.trim()}.`;
			inviteEmail = '';
			inviteOpen = false;
			await invalidateAll();
		} catch (e) {
			inviteErr = e instanceof ApiError ? e.message : 'Invite failed.';
		} finally {
			inviteBusy = false;
		}
	}

	/** @type {string|null} */
	let resendBusyId = $state(null);

	/**
	 * Re-POST the invite for a pending client user — the server regenerates
	 * the token and resends the email.
	 * @param {import('$lib/api/clients.js').ClientInvite} invite
	 */
	async function resendInvite(invite) {
		inviteErr = null;
		inviteMsg = null;
		resendBusyId = invite.id;
		try {
			await clientApi.createClientInvite(fetch, token, data.client.id, { email: invite.email });
			inviteMsg = `Invite resent to ${invite.email}.`;
			await invalidateAll();
		} catch (e) {
			inviteErr = e instanceof ApiError ? e.message : 'Resend failed.';
		} finally {
			resendBusyId = null;
		}
	}

	/** @type {{ id: string, email: string }|null} */
	let revokeTarget = $state(null);
	let revokeBusy = $state(false);

	async function revokeInvite() {
		if (!revokeTarget) return;
		revokeBusy = true;
		inviteErr = null;
		try {
			await clientApi.revokeClientInvite(fetch, token, revokeTarget.id);
			revokeTarget = null;
			await invalidateAll();
		} catch (e) {
			inviteErr = e instanceof ApiError ? e.message : 'Revoke failed.';
		} finally {
			revokeBusy = false;
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
				{#if canManage}
					<button
						type="button"
						onclick={() => {
							inviteErr = null;
							inviteMsg = null;
							inviteEmail = '';
							inviteOpen = true;
						}}
						class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Invite client user
					</button>
				{/if}
			</div>

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

			{#if data.client.client_users.length === 0}
				<p class="mt-3 text-sm text-slate-500">No contacts yet.</p>
			{:else}
				<ul class="mt-3 divide-y divide-slate-200">
					{#each data.client.client_users as u (u.id)}
						<li class="flex flex-wrap items-center justify-between gap-2 py-3">
							<div>
								<p class="text-sm font-medium text-slate-900">
									{u.full_name ?? u.email}
								</p>
								<p class="text-xs text-slate-500">{u.email}</p>
							</div>
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
						</li>
					{/each}
				</ul>
			{/if}

			<!-- Pending invites -->
			<div class="mt-6 border-t border-slate-200 pt-5">
				<h3 class="text-sm font-semibold text-slate-900">Pending invites</h3>
				{#if data.invites.length === 0}
					<p class="mt-2 text-sm text-slate-500">No pending invites.</p>
				{:else}
					<ul class="mt-2 divide-y divide-slate-200">
						{#each data.invites as invite (invite.id)}
							<li class="flex flex-wrap items-center justify-between gap-2 py-3">
								<div>
									<p class="text-sm font-medium text-slate-900">{invite.email}</p>
									<p class="text-xs text-slate-500">
										Expires {formatDateTime(invite.expires_at)}
									</p>
								</div>
								<div class="flex flex-wrap items-center gap-3">
									<StatusBadge status={invite.status} />
									{#if canManage && invite.status === 'pending'}
										<button
											type="button"
											disabled={resendBusyId === invite.id}
											aria-busy={resendBusyId === invite.id}
											onclick={() => resendInvite(invite)}
											class="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
										>
											{#if resendBusyId === invite.id}
												<Spinner class="h-3.5 w-3.5 text-indigo-600" />{/if}
											Resend
										</button>
										<button
											type="button"
											onclick={() => (revokeTarget = { id: invite.id, email: invite.email })}
											class="text-sm font-medium text-red-600 hover:text-red-500"
											aria-label={`Revoke invite for ${invite.email}`}
										>
											Revoke
										</button>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
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
								{#if n.author_id}
									· <span class="font-mono">{n.author_id.slice(0, 8)}</span>
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
						<li class="flex gap-3 text-sm">
							<div class="w-32 shrink-0 text-xs text-slate-500">
								{formatDateTime(a.created_at)}
							</div>
							<div class="flex-1">
								<p class="font-mono text-slate-800">{a.action}</p>
								<p class="text-xs text-slate-500">
									{a.entity_type}{#if a.entity_id}
										· {a.entity_id.slice(0, 8)}{/if}
									· {a.actor_type}
								</p>
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

<!-- Invite client user dialog -->
<Dialog.Root bind:open={inviteOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold text-slate-900">Invite client user</Dialog.Title>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				They will receive an email with a link to create their account and access {data.client
					.name}.
			</Dialog.Description>

			{#if inviteErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{inviteErr}
				</p>
			{/if}

			<form
				class="mt-4"
				onsubmit={(e) => {
					e.preventDefault();
					sendInvite();
				}}
			>
				<div>
					<label for="invite-email" class="block text-sm font-medium text-slate-700">Email</label>
					<input
						id="invite-email"
						type="email"
						bind:value={inviteEmail}
						required
						autocomplete="email"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={inviteBusy || !inviteEmail.trim()}
						aria-busy={inviteBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if inviteBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Send invite
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
	title="Revoke invite"
	description={revokeTarget ? `Revoke the pending invite for ${revokeTarget.email}?` : ''}
	confirmLabel="Revoke"
	destructive
	busy={revokeBusy}
	onconfirm={revokeInvite}
/>
