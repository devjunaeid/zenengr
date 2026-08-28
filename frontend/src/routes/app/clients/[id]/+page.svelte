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
	import officeBuilding from '@iconify-icons/mdi/office-building';
	import accountGroup from '@iconify-icons/mdi/account-group';
	import bookOpenOutline from '@iconify-icons/mdi/book-open-outline';
	import noteTextOutline from '@iconify-icons/mdi/note-text-outline';
	import history from '@iconify-icons/mdi/history';
	import cashMultiple from '@iconify-icons/mdi/cash-multiple';
	import pencilOutline from '@iconify-icons/mdi/pencil-outline';
	import archiveOutline from '@iconify-icons/mdi/archive-outline';
	import archiveArrowUpOutline from '@iconify-icons/mdi/archive-arrow-up-outline';
	import lockReset from '@iconify-icons/mdi/lock-reset';
	import accountCancelOutline from '@iconify-icons/mdi/account-cancel-outline';
	import accountCheckOutline from '@iconify-icons/mdi/account-check-outline';
	import keyOutline from '@iconify-icons/mdi/key-outline';
	import plus from '@iconify-icons/mdi/plus';
	import close from '@iconify-icons/mdi/close';
	import emailOutline from '@iconify-icons/mdi/email-outline';
	import phoneOutline from '@iconify-icons/mdi/phone-outline';
	import identifier from '@iconify-icons/mdi/identifier';
	import mapMarkerOutline from '@iconify-icons/mdi/map-marker-outline';
	import tagOutline from '@iconify-icons/mdi/tag-outline';

	let { data } = $props();

	const token = auth.token;
	let canManage = $derived(auth.can('manage', 'clients'));
	let isEmployee = $derived(auth.user?.role === 'employee');

	// Active tab state
	let activeTab = $state(page.url.searchParams.get('tab') || 'overview');

	function setTab(tabId) {
		activeTab = tabId;
		const params = new SvelteURLSearchParams(page.url.searchParams);
		if (tabId === 'overview') params.delete('tab');
		else params.set('tab', tabId);
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL query update
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}

	let userErr = $state(null);
	let userMsg = $state(null);

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
			setTimeout(() => (userMsg = null), 4000);
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Password change failed.';
		} finally {
			passwordBusy = false;
		}
	}

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
			setTimeout(() => (userMsg = null), 4000);
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Revoke failed.';
		} finally {
			revokeBusy = false;
		}
	}

	async function restoreAccess(u) {
		userErr = null;
		userMsg = null;
		try {
			await clientApi.reactivateClientUser(fetch, token, u.id);
			userMsg = `Access restored for ${u.email}.`;
			await invalidateAll();
			setTimeout(() => (userMsg = null), 4000);
		} catch (e) {
			userErr = e instanceof ApiError ? e.message : 'Restore failed.';
		}
	}

	let archiveAction = $state(null);
	let archiveBusy = $state(false);
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

	let noteBody = $state('');
	let noteBusy = $state(false);
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

	function gotoNotesPage(p) {
		const params = new SvelteURLSearchParams(page.url.searchParams);
		if (p > 1) params.set('notes_page', String(p));
		else params.delete('notes_page');
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL on the same page
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}

	function gotoActivityPage(p) {
		const params = new SvelteURLSearchParams(page.url.searchParams);
		if (p > 1) params.set('activity_page', String(p));
		else params.delete('activity_page');
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- relative URL on the same page
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}

	function fmtNumber(n) {
		if (n == null || n === '') return '—';
		const num = typeof n === 'string' ? Number(n) : n;
		if (Number.isNaN(num)) return '—';
		return new Intl.NumberFormat(undefined).format(num);
	}

	const TABS = [
		{ id: 'overview', label: 'Company Profile', icon: officeBuilding },
		{ id: 'contacts', label: 'Contacts & Portal', icon: accountGroup, countBadge: () => data.client.client_users.length },
		{ id: 'financials', label: 'Financials & Ledger', icon: cashMultiple },
		{ id: 'notes', label: 'Internal Notes', icon: noteTextOutline, countBadge: () => data.notes.total },
		{ id: 'activity', label: 'Activity Trail', icon: history, countBadge: () => data.activity.total }
	];
</script>

<svelte:head><title>{data.client.name} — ZenEngr</title></svelte:head>

<div class="space-y-6">
	<!-- Client Header Profile Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex items-center gap-4">
				<div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white font-bold text-base shadow-sm">
					{data.client.name.slice(0, 2).toUpperCase()}
				</div>
				<div>
					<div class="flex flex-wrap items-center gap-2.5">
						<h1 class="text-lg font-bold text-slate-900">{data.client.name}</h1>
						<StatusBadge status={data.client.status} />
						<span class="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
							{humanize(data.client.client_type)}
						</span>
					</div>
					<div class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
						{#if data.client.email}
							<span class="inline-flex items-center gap-1">
								<Icon icon={emailOutline} class="h-3.5 w-3.5 text-slate-400" />
								{data.client.email}
							</span>
						{/if}
						{#if data.client.phone}
							<span class="inline-flex items-center gap-1">
								<Icon icon={phoneOutline} class="h-3.5 w-3.5 text-slate-400" />
								{data.client.phone}
							</span>
						{/if}
						{#if data.client.tax_id}
							<span class="inline-flex items-center gap-1 font-mono text-[11px]">
								<Icon icon={identifier} class="h-3.5 w-3.5 text-slate-400" />
								Tax: {data.client.tax_id}
							</span>
						{/if}
					</div>
				</div>
			</div>

			<!-- Action Buttons -->
			{#if canManage}
				<div class="flex flex-wrap items-center gap-2">
					<a
						href={resolve('/app/clients/[id]/edit', { id: data.client.id })}
						class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition-colors"
					>
						<Icon icon={pencilOutline} class="h-3.5 w-3.5 text-slate-500" />
						Edit Profile
					</a>
					{#if data.client.status === 'active'}
						<button
							type="button"
							onclick={() => (archiveAction = 'archive')}
							class="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50/50 px-3.5 py-2 text-xs font-semibold text-red-700 shadow-2xs hover:bg-red-100/60 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none transition-colors"
						>
							<Icon icon={archiveOutline} class="h-3.5 w-3.5" />
							Archive
						</button>
					{:else}
						<button
							type="button"
							onclick={() => (archiveAction = 'unarchive')}
							class="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/50 px-3.5 py-2 text-xs font-semibold text-emerald-700 shadow-2xs hover:bg-emerald-100/60 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none transition-colors"
						>
							<Icon icon={archiveArrowUpOutline} class="h-3.5 w-3.5" />
							Unarchive
						</button>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Quick Metric KPI Pills Bar (Synced with Project Statements & Ledger) -->
		<div class="mt-5 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 border-t border-slate-100 pt-4">
			<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Active Projects</p>
				<p class="mt-1 text-base font-bold text-slate-900">{fmtNumber(data.client.active_projects)}</p>
			</div>
			<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Total Invoiced</p>
				<p class="mt-1 text-base font-bold text-slate-900">{fmtPrice(data.client.total_invoiced)}</p>
			</div>
			<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Total Paid</p>
				<p class="mt-1 text-base font-bold text-emerald-600">{fmtPrice(data.client.total_paid || 0)}</p>
			</div>
			<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Outstanding Due</p>
				<p class="mt-1 text-base font-bold {Number(data.client.total_outstanding) > 0 ? 'text-amber-600' : 'text-slate-900'}">
					{fmtPrice(data.client.total_outstanding)}
				</p>
			</div>
			<div class="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
				<p class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Advance Balance</p>
				<p class="mt-1 text-base font-bold {Number(data.ledger?.advance_balance || 0) > 0 ? 'text-indigo-600' : 'text-slate-900'}">
					{fmtPrice(data.ledger?.advance_balance || 0)}
				</p>
			</div>
		</div>
	</section>

	<!-- Alert Messages -->
	{#if isEmployee}
		<div role="status" class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs font-semibold text-amber-800 shadow-2xs">
			View only — contact an administrator to modify client records or access credentials.
		</div>
	{/if}
	{#if actionErr}
		<div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-800 shadow-2xs">
			{actionErr}
		</div>
	{/if}
	{#if userMsg}
		<div role="status" class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs font-semibold text-emerald-800 shadow-2xs">
			{userMsg}
		</div>
	{/if}
	{#if userErr}
		<div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-800 shadow-2xs">
			{userErr}
		</div>
	{/if}

	<!-- Segmented Pill Tabs Navigation Bar -->
	<div class="flex items-center gap-1.5 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-2xs">
		{#each TABS as tab (tab.id)}
			{@const active = activeTab === tab.id}
			{@const count = tab.countBadge ? tab.countBadge() : null}
			<button
				type="button"
				onclick={() => setTab(tab.id)}
				class="flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all {active
					? 'bg-indigo-600 text-white shadow-2xs'
					: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}"
			>
				<Icon icon={tab.icon} class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}" />
				<span>{tab.label}</span>
				{#if count != null}
					<span
						class="rounded-full px-1.5 py-0.2 text-[10px] font-bold {active
							? 'bg-indigo-700/80 text-white'
							: 'bg-slate-100 text-slate-600'}"
					>
						{count}
					</span>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Tab 1: Overview & Profile -->
	{#if activeTab === 'overview'}
		<div class="grid gap-6 md:grid-cols-2">
			<!-- Profile Card -->
			<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
				<div class="border-b border-slate-100 bg-slate-50/50 px-5 py-3.5">
					<h2 class="text-xs font-bold uppercase tracking-wider text-slate-600">Company Information</h2>
				</div>
				<div class="p-5 space-y-4">
					<div class="grid grid-cols-2 gap-4">
						<div>
							<dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Client Name</dt>
							<dd class="mt-1 text-xs font-bold text-slate-800">{data.client.name}</dd>
						</div>
						<div>
							<dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Type</dt>
							<dd class="mt-1 text-xs font-bold text-slate-800">{humanize(data.client.client_type)}</dd>
						</div>
						<div>
							<dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Primary Email</dt>
							<dd class="mt-1 text-xs text-slate-700">{data.client.email || '—'}</dd>
						</div>
						<div>
							<dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Phone</dt>
							<dd class="mt-1 text-xs text-slate-700">{data.client.phone || '—'}</dd>
						</div>
						<div>
							<dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Tax ID / VAT</dt>
							<dd class="mt-1 font-mono text-xs text-slate-700">{data.client.tax_id || '—'}</dd>
						</div>
						<div>
							<dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Status</dt>
							<dd class="mt-1"><StatusBadge status={data.client.status} /></dd>
						</div>
					</div>

					<div class="border-t border-slate-100 pt-3">
						<dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Tags &amp; Labels</dt>
						<dd>
							{#if data.client.tags && data.client.tags.length}
								<div class="flex flex-wrap gap-1.5">
									{#each data.client.tags as t (t)}
										<span class="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
											<Icon icon={tagOutline} class="h-3 w-3 text-slate-400" />
											{t}
										</span>
									{/each}
								</div>
							{:else}
								<span class="text-xs text-slate-400">No tags assigned.</span>
							{/if}
						</dd>
					</div>

					<div class="border-t border-slate-100 pt-3 grid grid-cols-2 gap-4 text-[11px] text-slate-400">
						<div>
							<span>Created: </span>
							<span class="text-slate-600 font-medium">{formatDateTime(data.client.created_at)}</span>
						</div>
						<div>
							<span>Last Updated: </span>
							<span class="text-slate-600 font-medium">{formatDateTime(data.client.updated_at)}</span>
						</div>
					</div>
				</div>
			</section>

			<!-- Address & Billing Card -->
			<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
				<div class="border-b border-slate-100 bg-slate-50/50 px-5 py-3.5">
					<h2 class="text-xs font-bold uppercase tracking-wider text-slate-600">Billing Address &amp; Location</h2>
				</div>
				<div class="p-5">
					{#if formatAddress(data.client.billing_address)}
						<div class="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50/50 p-4">
							<Icon icon={mapMarkerOutline} class="h-5 w-5 text-indigo-600 shrink-0 mt-0.5" />
							<address class="text-xs text-slate-700 leading-relaxed not-italic whitespace-pre-line">
								{formatAddress(data.client.billing_address)}
							</address>
						</div>
					{:else}
						<div class="p-8 text-center text-xs text-slate-400">
							<Icon icon={mapMarkerOutline} class="mx-auto h-8 w-8 text-slate-300 mb-2" />
							No billing address recorded for this client.
						</div>
					{/if}
				</div>
			</section>
		</div>
	{/if}

	<!-- Tab 2: Contacts & Portal Users -->
	{#if activeTab === 'contacts'}
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 bg-slate-50/50 px-5 py-3.5">
				<div>
					<h2 class="text-xs font-bold uppercase tracking-wider text-slate-700">Client Portal Users &amp; Contacts</h2>
					<p class="text-[11px] text-slate-400 mt-0.5">Authorised representatives with access to the client portal.</p>
				</div>
				<span class="inline-flex items-center rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
					{data.client.client_users.length} {data.client.client_users.length === 1 ? 'user' : 'users'}
				</span>
			</div>

			{#if data.client.client_users.length === 0}
				<div class="p-12 text-center text-xs text-slate-400">
					<Icon icon={accountGroup} class="mx-auto h-8 w-8 text-slate-300 mb-2" />
					<p class="font-bold text-slate-800">No client portal users added yet</p>
					<p class="mt-1">Add client contacts from the Edit Client page to grant them portal access.</p>
				</div>
			{:else}
				<div class="divide-y divide-slate-100">
					{#each data.client.client_users as u (u.id)}
						<div class="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between hover:bg-slate-50/60 transition-colors">
							<div class="flex items-center gap-3.5">
								<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 font-bold text-indigo-700 text-xs">
									{(u.full_name || u.email).slice(0, 2).toUpperCase()}
								</div>
								<div>
									<div class="flex items-center gap-2">
										<p class="text-xs font-bold text-slate-900">{u.full_name || u.email}</p>
										{#if u.is_primary_billing_contact}
											<span class="rounded-md bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-700 ring-1 ring-inset ring-indigo-600/20">
												Primary Billing
											</span>
										{/if}
										<span class="rounded-md px-2 py-0.5 text-[10px] font-bold {u.is_active ? 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20' : 'bg-slate-100 text-slate-600'}">
											{u.is_active ? 'Active' : 'Deactivated'}
										</span>
									</div>
									<p class="text-xs text-slate-500 mt-0.5">{u.email}</p>
								</div>
							</div>

							{#if canManage}
								<div class="flex flex-wrap items-center gap-2 pt-2 sm:pt-0">
									<button
										type="button"
										onclick={() => {
											userErr = null;
											userMsg = null;
											newPassword = '';
											confirmPassword = '';
											passwordUser = u;
										}}
										class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition-colors"
									>
										<Icon icon={keyOutline} class="h-3.5 w-3.5 text-slate-500" />
										Change Password
									</button>
									{#if u.is_active}
										<button
											type="button"
											onclick={() => {
												userErr = null;
												revokeTarget = u;
											}}
											class="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50/40 px-3 py-1.5 text-xs font-semibold text-red-700 shadow-2xs hover:bg-red-100/60 transition-colors"
										>
											<Icon icon={accountCancelOutline} class="h-3.5 w-3.5" />
											Revoke Access
										</button>
									{:else}
										<button
											type="button"
											onclick={() => restoreAccess(u)}
											class="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/40 px-3 py-1.5 text-xs font-semibold text-emerald-700 shadow-2xs hover:bg-emerald-100/60 transition-colors"
										>
											<Icon icon={accountCheckOutline} class="h-3.5 w-3.5" />
											Restore Access
										</button>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}

	<!-- Tab 3: Financials & Ledger -->
	{#if activeTab === 'financials'}
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/50 px-5 py-3.5">
				<div>
					<h2 class="text-xs font-bold uppercase tracking-wider text-slate-700">Client Statement Ledger</h2>
					<p class="text-[11px] text-slate-400 mt-0.5">Chronological record of invoices, advances, and applied payments.</p>
				</div>
				{#if data.ledger}
					<div class="rounded-lg bg-indigo-50/70 border border-indigo-100 px-3 py-1.5 text-xs font-semibold text-indigo-900">
						Advance Balance: <span class="font-bold text-indigo-700">{fmtPrice(data.ledger.advance_balance)}</span>
					</div>
				{/if}
			</div>

			{#if data.ledger && data.ledger.entries && data.ledger.entries.length > 0}
				<LedgerTable entries={data.ledger.entries} />
			{:else}
				<div class="p-12 text-center text-xs text-slate-400">
					<Icon icon={cashMultiple} class="mx-auto h-8 w-8 text-slate-300 mb-2" />
					No transactions or ledger records recorded for this client yet.
				</div>
			{/if}
		</section>
	{/if}

	<!-- Tab 4: Internal Notes -->
	{#if activeTab === 'notes'}
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="border-b border-slate-100 bg-slate-50/50 px-5 py-3.5">
				<h2 class="text-xs font-bold uppercase tracking-wider text-slate-700">Team Internal Notes</h2>
				<p class="text-[11px] text-slate-400 mt-0.5">Private notes shared with your internal team (not visible to client).</p>
			</div>

			<div class="p-5 space-y-5">
				{#if canManage}
					{#if noteErr}
						<div role="alert" class="rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-800">
							{noteErr}
						</div>
					{/if}
					<form
						onsubmit={(e) => {
							e.preventDefault();
							addNote();
						}}
						class="space-y-3"
					>
						<textarea
							id="note-body"
							bind:value={noteBody}
							rows="3"
							placeholder="Add an internal note or observation..."
							class="block w-full rounded-xl border border-slate-300 bg-slate-50/40 p-3 text-xs shadow-2xs focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
						></textarea>
						<div class="flex justify-end">
							<button
								type="submit"
								disabled={noteBusy || !noteBody.trim()}
								aria-busy={noteBusy}
								class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60 transition-colors"
							>
								{#if noteBusy}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
								Add Note
							</button>
						</div>
					</form>
				{/if}

				{#if data.notes.items.length === 0}
					<div class="rounded-xl border border-slate-100 bg-slate-50/50 p-8 text-center text-xs text-slate-400">
						<Icon icon={noteTextOutline} class="mx-auto h-8 w-8 text-slate-300 mb-2" />
						No internal notes created yet.
					</div>
				{:else}
					<ul class="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
						{#each data.notes.items as n (n.id)}
							<li class="p-4 hover:bg-slate-50/60 transition-colors">
								<p class="text-xs whitespace-pre-wrap text-slate-800 leading-relaxed">{n.body}</p>
								<div class="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
									<span class="font-semibold text-slate-600">{n.author_name ?? 'Staff Member'}</span>
									<span>·</span>
									<span>{formatDateTime(n.created_at)}</span>
								</div>
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
			</div>
		</section>
	{/if}

	<!-- Tab 5: Activity Trail -->
	{#if activeTab === 'activity'}
		<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
			<div class="border-b border-slate-100 bg-slate-50/50 px-5 py-3.5">
				<h2 class="text-xs font-bold uppercase tracking-wider text-slate-700">Client Activity &amp; Audit Trail</h2>
				<p class="text-[11px] text-slate-400 mt-0.5">Immutable activity stream of client events and updates.</p>
			</div>

			{#if data.activity.items.length === 0}
				<div class="p-12 text-center text-xs text-slate-400">
					<Icon icon={history} class="mx-auto h-8 w-8 text-slate-300 mb-2" />
					No activity recorded for this client yet.
				</div>
			{:else}
				<div class="divide-y divide-slate-100">
					{#each data.activity.items as a (a.id)}
						{@const rows = formatClientActivityDetails(a.details)}
						<div class="flex gap-3.5 p-4 hover:bg-slate-50/60 transition-colors">
							<span class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
								<Icon icon={groupIcon(auditGroup(a.action))} class="h-4 w-4 text-indigo-600" />
							</span>
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
									<span class="text-xs font-bold text-slate-900">{auditActionLabel(a.action)}</span>
									<span class="text-[11px] text-slate-400">{formatDateTime(a.created_at)}</span>
								</div>
								<div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-slate-500">
									<span class="rounded-md bg-slate-100 px-1.5 py-0.5 font-semibold text-slate-600">
										{a.actor_name || (a.actor_type ? humanize(a.actor_type) : 'System')}
									</span>
									<span>{a.entity_label || (a.entity_type ? humanize(a.entity_type) : '—')}</span>
								</div>
								{#if rows.length > 0}
									<details class="mt-1.5">
										<summary class="cursor-pointer text-[11px] font-semibold text-indigo-600 select-none hover:text-indigo-700">
											Event Details
										</summary>
										<dl class="mt-2 space-y-1 rounded-lg border border-slate-100 bg-slate-50 p-2.5">
											{#each rows as row, idx (`${row.label}-${idx}`)}
												<div class="flex gap-2 text-[11px]">
													<dt class="w-28 shrink-0 font-medium text-slate-400">{row.label}</dt>
													<dd class="min-w-0 break-words font-medium text-slate-700">{row.value}</dd>
												</div>
											{/each}
										</dl>
									</details>
								{/if}
							</div>
						</div>
					{/each}
				</div>
				<div class="p-4 border-t border-slate-100">
					<Pagination
						page={data.activity.page}
						pageSize={data.activity.page_size}
						total={data.activity.total}
						onpage={gotoActivityPage}
					/>
				</div>
			{/if}
		</section>
	{/if}
</div>

<!-- Archive / Unarchive Client Modal -->
<ConfirmDialog
	bind:open={
		() => archiveAction !== null,
		(v) => {
			if (!v) archiveAction = null;
		}
	}
	title={archiveAction === 'archive' ? 'Archive Client' : 'Unarchive Client'}
	description={archiveAction === 'archive'
		? `Archive ${data.client.name}? It will no longer appear in default client lists.`
		: `Unarchive ${data.client.name}? It will become active again.`}
	confirmLabel={archiveAction === 'archive' ? 'Archive Client' : 'Unarchive Client'}
	destructive={archiveAction === 'archive'}
	busy={archiveBusy}
	onconfirm={runArchiveAction}
/>

<!-- Change Password Modal Dialog -->
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
		<Dialog.Overlay class="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs animate-fade-in" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-2xl border border-slate-100 focus:outline-none animate-in"
		>
			<div class="flex items-center justify-between border-b border-slate-100 pb-4">
				<div class="flex items-center gap-2.5">
					<div class="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
						<Icon icon={keyOutline} class="h-5 w-5" />
					</div>
					<div>
						<Dialog.Title class="text-sm font-bold text-slate-900">Change Portal Password</Dialog.Title>
						{#if passwordUser}
							<Dialog.Description class="text-xs text-slate-500 mt-0.5">
								Set a new password for {passwordUser.email}.
							</Dialog.Description>
						{/if}
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

			{#if userErr}
				<div role="alert" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-800">
					{userErr}
				</div>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					changePassword();
				}}
			>
				<div>
					<label for="pw-new" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
						New Password *
					</label>
					<input
						id="pw-new"
						type="password"
						bind:value={newPassword}
						required
						minlength="10"
						autocomplete="new-password"
						placeholder="Minimum 10 characters"
						class="block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="pw-confirm" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
						Confirm Password *
					</label>
					<input
						id="pw-confirm"
						type="password"
						bind:value={confirmPassword}
						required
						minlength="10"
						autocomplete="new-password"
						placeholder="Re-enter password"
						class="block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-xs shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					/>
				</div>

				{#if newPassword && confirmPassword && newPassword !== confirmPassword}
					<p role="alert" class="text-xs text-red-600 font-medium">Passwords do not match.</p>
				{/if}

				<div class="mt-6 flex justify-end gap-2.5 pt-3 border-t border-slate-100">
					<Dialog.Close
						type="button"
						onclick={() => {
							userErr = null;
							passwordUser = null;
						}}
						class="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={passwordBusy || !newPassword || newPassword !== confirmPassword}
						aria-busy={passwordBusy}
						class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:opacity-60 transition-colors"
					>
						{#if passwordBusy}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
						Update Password
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Revoke Access Modal Dialog -->
<ConfirmDialog
	bind:open={
		() => revokeTarget !== null,
		(v) => {
			if (!v) revokeTarget = null;
		}
	}
	title="Revoke Portal Access"
	description={revokeTarget
		? `Revoke client portal access for ${revokeTarget.email}? They will no longer be able to log in to the portal.`
		: ''}
	confirmLabel="Revoke Access"
	destructive
	busy={revokeBusy}
	onconfirm={revokeAccess}
/>
