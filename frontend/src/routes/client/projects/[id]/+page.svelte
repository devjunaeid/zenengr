<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { ApiError } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import CommentThread from '$lib/components/CommentThread.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import CopyBadge from '$lib/components/CopyBadge.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';
	import { fmtBytes, formatDate, fmtPrice, humanize } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import arrowLeft from '@iconify-icons/mdi/arrow-left';
	import viewDashboard from '@iconify-icons/mdi/view-dashboard';
	import formatListChecks from '@iconify-icons/mdi/format-list-checks';
	import cashMultiple from '@iconify-icons/mdi/cash-multiple';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import downloadOutline from '@iconify-icons/mdi/download-outline';
	import printerOutline from '@iconify-icons/mdi/printer-outline';
	import checkCircle from '@iconify-icons/mdi/check-circle';
	import clockOutline from '@iconify-icons/mdi/clock-outline';
	import alertCircleOutline from '@iconify-icons/mdi/alert-circle-outline';
	import fileDocumentOutline from '@iconify-icons/mdi/file-document-outline';
	import arrowDown from '@iconify-icons/mdi/arrow-down';
	import arrowUp from '@iconify-icons/mdi/arrow-up';
	import plusCircle from '@iconify-icons/mdi/plus-circle';
	import minusCircle from '@iconify-icons/mdi/minus-circle';

	let { data } = $props();

	const token = /** @type {string} */ (portalAuth.token);

	// Tabs state
	let activeTab = $state(page.url.searchParams.get('tab') || 'overview');

	function setTab(tabId) {
		activeTab = tabId;
		const params = new SvelteURLSearchParams(page.url.searchParams);
		if (tabId === 'overview') {
			params.delete('tab');
		} else {
			params.set('tab', tabId);
		}
		const qs = params.toString();
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		goto(qs ? `?${qs}` : '?', { keepFocus: true, noScroll: true });
	}

	let downloadErr = $state(/** @type {string|null} */ (null));
	let statementPdfBusy = $state(false);

	async function runDownload(file) {
		downloadErr = null;
		try {
			await portalApi.downloadClientFile(fetch, token, file.id, file.name);
		} catch (e) {
			downloadErr = e instanceof ApiError ? e.message : 'Download failed.';
		}
	}

	async function downloadStatementPdf() {
		if (statementPdfBusy) return;
		statementPdfBusy = true;
		try {
			const res = await fetch(`/api/v1/client/projects/${encodeURIComponent(data.project.id)}/statement/pdf`, {
				headers: { Authorization: `Bearer ${token}` }
			});
			if (!res.ok) throw new Error('Could not download statement PDF');
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `statement-${data.project.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.pdf`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (e) {
			downloadErr = e instanceof Error ? e.message : 'Could not download statement PDF.';
		} finally {
			statementPdfBusy = false;
		}
	}

	// ---- ledger data ----
	let ledgerData = $derived(data.ledger);
	let ledgerEntries = $derived(
		(ledgerData?.entries ?? []).slice().sort((a, b) => {
			const da = a.entry_date ?? a.created_at;
			const db = b.entry_date ?? b.created_at;
			return da < db ? -1 : da > db ? 1 : 0;
		})
	);
	let ledgerSummary = $derived(ledgerData?.summary ?? null);

	function entryMeta(e) {
		const n = Number(e.amount) || 0;
		if (e.type === 'payment') {
			return { icon: arrowDown, text: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' };
		}
		if (e.type === 'refund' || n < 0) {
			return {
				icon: e.type === 'refund' ? arrowUp : minusCircle,
				text: 'text-red-600',
				bg: 'bg-red-50 border-red-200'
			};
		}
		return { icon: plusCircle, text: 'text-slate-700', bg: 'bg-slate-50 border-slate-200' };
	}

	function entryPrice(e) {
		const n = Number(e.amount) || 0;
		if (e.type === 'payment') return `+${fmtPrice(e.amount)}`;
		if (e.type === 'refund') return `−${fmtPrice(Math.abs(n))}`;
		if (n < 0) return `−${fmtPrice(Math.abs(n))}`;
		return fmtPrice(e.amount);
	}

	const TABS = [
		{ id: 'overview', label: 'Overview & Milestones', icon: viewDashboard },
		{ id: 'services', label: 'Services & Scope', icon: formatListChecks, count: () => data.project.services.length },
		{ id: 'financials', label: 'Statement & Financials', icon: cashMultiple },
		{ id: 'invoices', label: 'Invoices', icon: receiptText, count: () => data.project.linked_invoices?.length || 0 },
		{ id: 'files', label: 'Files & Assets', icon: folderMultiple, count: () => data.files.total }
	];
</script>

<svelte:head><title>{data.project.name} — Client Portal</title></svelte:head>

<div class="space-y-6">
	<!-- Breadcrumb Navigation -->
	<nav aria-label="Breadcrumb" class="text-xs font-semibold text-slate-500">
		<ol class="flex items-center gap-1.5">
			<li>
				<a href={resolve('/client/projects')} class="hover:text-indigo-600 flex items-center gap-1">
					<Icon icon={arrowLeft} class="h-3.5 w-3.5" />
					Projects
				</a>
			</li>
			<li aria-hidden="true" class="text-slate-300">/</li>
			<li class="font-bold text-slate-800">{data.project.name}</li>
		</ol>
	</nav>

	<!-- Project Header Card -->
	<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<div class="flex flex-wrap items-center gap-2.5">
					<h1 class="text-xl font-bold text-slate-900">{data.project.name}</h1>
					<CopyBadge value={data.project.id} />
					<StatusBadge status={data.project.status} />
				</div>
				{#if data.project.start_date}
					<p class="mt-1 text-xs text-slate-500">
						Project started on <span class="font-semibold text-slate-700">{formatDate(data.project.start_date)}</span>
					</p>
				{/if}
			</div>

			<!-- Quick Financial Summary Badges -->
			{#if ledgerSummary}
				<div class="flex items-center gap-3">
					<div class="rounded-xl border border-slate-100 bg-slate-50/80 px-3.5 py-2 text-right">
						<span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total</span>
						<p class="text-sm font-bold text-slate-900">{fmtPrice(ledgerSummary.total)}</p>
					</div>
					<div class="rounded-xl border border-slate-100 bg-slate-50/80 px-3.5 py-2 text-right">
						<span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Due</span>
						<p class="text-sm font-bold {Number(ledgerSummary.due) > 0 ? 'text-amber-600' : 'text-slate-900'}">
							{fmtPrice(ledgerSummary.due)}
						</p>
					</div>
				</div>
			{/if}
		</div>

		<!-- Smart Navigation Pill Tabs -->
		<div class="mt-6 flex flex-wrap gap-1.5 border-t border-slate-100 pt-4">
			{#each TABS as tab (tab.id)}
				{@const count = tab.count ? tab.count() : null}
				{@const active = activeTab === tab.id}
				<button
					type="button"
					onclick={() => setTab(tab.id)}
					class="inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-semibold transition-all {active
						? 'bg-indigo-600 text-white shadow-2xs'
						: 'bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900'}"
				>
					<Icon icon={tab.icon} class="h-4 w-4 shrink-0 {active ? 'text-white' : 'text-slate-400'}" />
					{tab.label}
					{#if count !== null && count > 0}
						<span class="ml-0.5 rounded-full px-1.5 py-0.2 text-[10px] font-bold {active ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'}">
							{count}
						</span>
					{/if}
				</button>
			{/each}
		</div>
	</section>

	{#if downloadErr}
		<div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 shadow-2xs">
			{downloadErr}
		</div>
	{/if}

	<!-- Tab 1: Overview & Milestones -->
	{#if activeTab === 'overview'}
		<div class="space-y-6">
			<!-- Milestone Progress Track -->
			<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
				<div class="flex items-center justify-between pb-4 border-b border-slate-100">
					<div>
						<h2 class="text-sm font-bold text-slate-900">Milestones & Timeline</h2>
						<p class="text-xs text-slate-500 mt-0.5">Track deliverables and schedule progress</p>
					</div>
					<div class="text-right">
						<span class="text-xs font-bold text-slate-900">
							{data.project.milestone_completion_pct}% Complete
						</span>
					</div>
				</div>

				{#if data.project.milestones.length === 0}
					<div class="py-8 text-center">
						<p class="text-xs text-slate-500">No scheduled milestones set for this project.</p>
					</div>
				{:else}
					<div class="mt-6 space-y-4">
						{#each data.project.milestones as m (m.id)}
							<div class="flex items-start gap-3.5 p-3 rounded-xl border border-slate-100 bg-slate-50/50">
								<div class="mt-0.5">
									{#if m.status === 'completed'}
										<Icon icon={checkCircle} class="h-5 w-5 text-emerald-600" />
									{:else if m.status === 'in_progress'}
										<Icon icon={clockOutline} class="h-5 w-5 text-indigo-600" />
									{:else}
										<Icon icon={alertCircleOutline} class="h-5 w-5 text-slate-400" />
									{/if}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center justify-between gap-2">
										<h3 class="text-xs font-bold text-slate-900">{m.name}</h3>
										<StatusBadge status={m.status} />
									</div>
									<div class="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
										{#if m.planned_date}
											<span>Target: {formatDate(m.planned_date)}</span>
										{/if}
										{#if m.actual_date}
											<span class="text-emerald-700">Completed: {formatDate(m.actual_date)}</span>
										{/if}
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Communication Thread -->
			<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
				<h2 class="text-sm font-bold text-slate-900 mb-4">Project Comments & Updates</h2>
				<CommentThread projectId={data.project.id} fetch={fetch} token={token} realm="client" staff={false} />
			</section>
		</div>

	<!-- Tab 2: Services & Scope -->
	{:else if activeTab === 'services'}
		<section class="rounded-xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
			<div class="border-b border-slate-100 p-5">
				<h2 class="text-sm font-bold text-slate-900">Project Services & Scope</h2>
				<p class="text-xs text-slate-500 mt-0.5">Active services and contract deliverables</p>
			</div>

			{#if data.project.services.length === 0}
				<div class="p-8 text-center">
					<p class="text-xs text-slate-500">No attached services listed.</p>
				</div>
			{:else}
				<div class="divide-y divide-slate-100">
					{#each data.project.services as s (s.id)}
						<div class="flex items-center justify-between p-4.5 hover:bg-slate-50/50 transition-colors">
							<div>
								<h3 class="text-xs font-bold text-slate-900">{s.service_name}</h3>
								<div class="mt-1">
									<StatusBadge status={s.status} />
								</div>
							</div>
							{#if s.price_at_attachment}
								<span class="text-xs font-bold text-slate-900 font-mono">
									{fmtPrice(s.price_at_attachment)}
								</span>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</section>

	<!-- Tab 3: Statement & Financials -->
	{:else if activeTab === 'financials'}
		<div class="space-y-6">
			<!-- Statement Summary Banner -->
			{#if ledgerSummary}
				<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
					<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-100">
						<div>
							<h2 class="text-sm font-bold text-slate-900">Project Financial Statement</h2>
							<p class="text-xs text-slate-500 mt-0.5">Real-time ledger summary of charges and payments</p>
						</div>
						<button
							type="button"
							onclick={downloadStatementPdf}
							disabled={statementPdfBusy}
							class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 transition-colors disabled:opacity-60"
						>
							{#if statementPdfBusy}
								<Spinner class="h-3.5 w-3.5 text-white" />
							{:else}
								<Icon icon={downloadOutline} class="h-3.5 w-3.5" />
							{/if}
							Download Statement PDF
						</button>
					</div>

					<div class="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
						<div class="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
							<span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subtotal</span>
							<p class="mt-1 text-base font-bold text-slate-900">{fmtPrice(ledgerSummary.subtotal)}</p>
						</div>
						<div class="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
							<span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Total Billed</span>
							<p class="mt-1 text-base font-bold text-slate-900">{fmtPrice(ledgerSummary.total)}</p>
						</div>
						<div class="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
							<span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Total Paid</span>
							<p class="mt-1 text-base font-bold text-emerald-600">{fmtPrice(ledgerSummary.paid)}</p>
						</div>
						<div class="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
							<span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Balance Due</span>
							<p class="mt-1 text-base font-bold {Number(ledgerSummary.due) > 0 ? 'text-amber-600' : 'text-slate-900'}">
								{fmtPrice(ledgerSummary.due)}
							</p>
						</div>
					</div>
				</section>
			{/if}

			<!-- Detailed Ledger Stream -->
			<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
				<h3 class="text-sm font-bold text-slate-900 mb-4">Transaction History & Charges</h3>
				{#if ledgerEntries.length === 0}
					<div class="py-8 text-center">
						<p class="text-xs text-slate-500">No ledger transactions recorded for this project yet.</p>
					</div>
				{:else}
					<div class="divide-y divide-slate-100">
						{#each ledgerEntries as e (e.id)}
							{@const meta = entryMeta(e)}
							<div class="flex items-center justify-between py-3.5 hover:bg-slate-50/60 transition-colors">
								<div class="flex items-center gap-3">
									<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border {meta.bg}">
										<Icon icon={meta.icon} class="h-4 w-4 {meta.text}" />
									</div>
									<div>
										<p class="text-xs font-bold text-slate-900">
											{e.description || humanize(e.type)}
										</p>
										<p class="text-[11px] text-slate-500">
											{formatDate(e.entry_date ?? e.created_at)}
											{#if e.invoice_number}
												· Ref: {e.invoice_number}
											{/if}
										</p>
									</div>
								</div>
								<span class="text-xs font-bold font-mono {meta.text}">
									{entryPrice(e)}
								</span>
							</div>
						{/each}
					</div>
				{/if}
			</section>
		</div>

	<!-- Tab 4: Invoices -->
	{:else if activeTab === 'invoices'}
		<section class="rounded-xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
			<div class="border-b border-slate-100 p-5">
				<h2 class="text-sm font-bold text-slate-900">Project Invoices</h2>
				<p class="text-xs text-slate-500 mt-0.5">All issued bills and payment requests</p>
			</div>

			{#if !data.project.linked_invoices || data.project.linked_invoices.length === 0}
				<div class="p-8 text-center">
					<p class="text-xs text-slate-500">No invoices have been issued for this project.</p>
				</div>
			{:else}
				<div class="divide-y divide-slate-100">
					{#each data.project.linked_invoices as inv (inv.id)}
						<div class="flex items-center justify-between p-4.5 hover:bg-slate-50/50 transition-colors">
							<div>
								<a
									href={resolve('/client/invoices/[id]', { id: inv.id })}
									class="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1.5"
								>
									<Icon icon={fileDocumentOutline} class="h-4 w-4 text-slate-400" />
									{inv.invoice_number ?? 'Invoice'}
								</a>
								<div class="mt-1">
									<StatusBadge status={inv.status} />
								</div>
							</div>
							<div class="flex items-center gap-4">
								<span class="text-xs font-bold text-slate-900 font-mono">
									{fmtPrice(inv.total)}
								</span>
								<a
									href={resolve('/client/invoices/[id]', { id: inv.id })}
									class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
								>
									<Icon icon={printerOutline} class="h-3.5 w-3.5 text-slate-500" />
									View / Print
								</a>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</section>

	<!-- Tab 5: Files & Assets -->
	{:else if activeTab === 'files'}
		<section class="rounded-xl border border-slate-200 bg-white shadow-2xs overflow-hidden">
			<div class="border-b border-slate-100 p-5">
				<h2 class="text-sm font-bold text-slate-900">Project Files & Documents</h2>
				<p class="text-xs text-slate-500 mt-0.5">Shared assets and project deliverables</p>
			</div>

			{#if data.files.items.length === 0}
				<div class="p-8 text-center">
					<p class="text-xs text-slate-500">No shared files uploaded for this project yet.</p>
				</div>
			{:else}
				<div class="divide-y divide-slate-100">
					{#each data.files.items as f (f.id)}
						<div class="flex items-center justify-between p-4.5 hover:bg-slate-50/50 transition-colors">
							<div class="flex items-center gap-3">
								<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
									<Icon icon={fileDocumentOutline} class="h-4 w-4" />
								</div>
								<div>
									<p class="text-xs font-bold text-slate-900">{f.name}</p>
									<p class="text-[11px] text-slate-500">
										{fmtBytes(f.size_bytes)} · Uploaded {formatDate(f.created_at)}
									</p>
								</div>
							</div>
							<button
								type="button"
								onclick={() => runDownload(f)}
								class="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
							>
								<Icon icon={downloadOutline} class="h-3.5 w-3.5" />
								Download
							</button>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}
</div>
