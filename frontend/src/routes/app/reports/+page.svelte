<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import ClientPicker from '$lib/components/ClientPicker.svelte';
	import ProjectPicker from '$lib/components/ProjectPicker.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { fmtPrice } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import calendarRange from '@iconify-icons/mdi/calendar-range';
	import refresh from '@iconify-icons/mdi/refresh';
	import download from '@iconify-icons/mdi/download';
	import folderMultiple from '@iconify-icons/mdi/folder-multiple';
	import accountMultiple from '@iconify-icons/mdi/account-multiple';
	import cogBox from '@iconify-icons/mdi/cog-box';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import cashMultiple from '@iconify-icons/mdi/cash-multiple';
	import alertCircleOutline from '@iconify-icons/mdi/alert-circle-outline';
	import walletOutline from '@iconify-icons/mdi/wallet-outline';
	import magnify from '@iconify-icons/mdi/magnify';
	import { SvelteURLSearchParams } from 'svelte/reactivity';

	let { data } = $props();

	// Active tab: 'timeline' | 'projects' | 'clients'
	let activeTab = $state('timeline');

	// Search & sort states for sub-tables
	let projectSearch = $state('');
	let projectSort = $state('due_desc'); // 'due_desc' | 'invoiced_desc' | 'name_asc'
	let clientSearch = $state('');
	let clientSort = $state('due_desc'); // 'due_desc' | 'invoiced_desc' | 'name_asc'

	// Filter state bound to inputs
	let selectedPreset = $state(data.filters.preset || 'this_month');
	let customFrom = $state(data.filters.date_from || '');
	let customTo = $state(data.filters.date_to || '');
	let selectedClientId = $state(data.filters.client_id || '');
	let selectedProjectId = $state(data.filters.project_id || '');
	let selectedGranularity = $state(data.filters.granularity || 'month');

	const PRESETS = [
		{ id: 'this_month', label: 'This Month' },
		{ id: 'last_month', label: 'Last Month' },
		{ id: 'this_quarter', label: 'This Quarter' },
		{ id: 'ytd', label: 'Year to Date' },
		{ id: 'last_30_days', label: 'Last 30 Days' },
		{ id: 'last_90_days', label: 'Last 90 Days' },
		{ id: 'all_time', label: 'All Time' },
		{ id: 'custom', label: 'Custom' }
	];

	function applyFilters(newPreset = selectedPreset) {
		const sp = new SvelteURLSearchParams();
		sp.set('preset', newPreset);
		if (newPreset === 'custom') {
			if (customFrom) sp.set('date_from', customFrom);
			if (customTo) sp.set('date_to', customTo);
		}
		if (selectedClientId) sp.set('client_id', selectedClientId);
		if (selectedProjectId) sp.set('project_id', selectedProjectId);
		if (selectedGranularity && selectedGranularity !== 'month') {
			sp.set('granularity', selectedGranularity);
		}
		const url = `${resolve('/app/reports')}?${sp.toString()}`;
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(url, { keepFocus: true, noScroll: true });
	}

	function selectPreset(presetId) {
		selectedPreset = presetId;
		if (presetId !== 'custom') {
			applyFilters(presetId);
		}
	}

	function resetFilters() {
		selectedPreset = 'this_month';
		customFrom = '';
		customTo = '';
		selectedClientId = '';
		selectedProjectId = '';
		selectedGranularity = 'month';
		const url = `${resolve('/app/reports')}?preset=this_month`;
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(url, { keepFocus: true, noScroll: true });
	}

	// Filtered & sorted projects
	let filteredProjects = $derived.by(() => {
		let list = data.ledgerData.projects || [];
		if (projectSearch.trim()) {
			const q = projectSearch.trim().toLowerCase();
			list = list.filter(
				(p) =>
					p.name.toLowerCase().includes(q) ||
					p.short_id.toLowerCase().includes(q) ||
					p.client_name.toLowerCase().includes(q)
			);
		}
		return [...list].sort((a, b) => {
			if (projectSort === 'due_desc') return Number(b.balance_due) - Number(a.balance_due);
			if (projectSort === 'invoiced_desc')
				return Number(b.total_invoiced) - Number(a.total_invoiced);
			if (projectSort === 'name_asc') return a.name.localeCompare(b.name);
			return 0;
		});
	});

	// Filtered & sorted clients
	let filteredClients = $derived.by(() => {
		let list = data.ledgerData.clients || [];
		if (clientSearch.trim()) {
			const q = clientSearch.trim().toLowerCase();
			list = list.filter((c) => c.name.toLowerCase().includes(q));
		}
		return [...list].sort((a, b) => {
			if (clientSort === 'due_desc') return Number(b.total_due) - Number(a.total_due);
			if (clientSort === 'invoiced_desc')
				return Number(b.total_invoiced) - Number(a.total_invoiced);
			if (clientSort === 'name_asc') return a.name.localeCompare(b.name);
			return 0;
		});
	});

	// Max timeline volume for bar calculations
	let maxTimelineVolume = $derived.by(() => {
		let max = 1;
		for (const item of data.ledgerData.timeline || []) {
			const inv = Number(item.invoiced_amount) || 0;
			const coll = Number(item.collected_amount) || 0;
			if (inv > max) max = inv;
			if (coll > max) max = coll;
		}
		return max;
	});

	// Export active dataset to CSV
	function exportActiveTableToCsv() {
		let filename = `zenengr-reports-${activeTab}-${new Date().toISOString().slice(0, 10)}.csv`;
		let rows = [];

		if (activeTab === 'timeline') {
			rows.push([
				'Period',
				'New Projects',
				'New Clients',
				'New Services',
				'Invoiced Amount',
				'Collected Amount',
				'Net Due Generated'
			]);
			for (const t of data.ledgerData.timeline || []) {
				rows.push([
					t.period_label,
					t.new_projects,
					t.new_clients,
					t.new_services,
					t.invoiced_amount,
					t.collected_amount,
					t.net_due_change
				]);
			}
		} else if (activeTab === 'projects') {
			rows.push([
				'Project ID',
				'Project Name',
				'Client Name',
				'Status',
				'Services Count',
				'Total Value',
				'Total Invoiced',
				'Total Paid',
				'Balance Due'
			]);
			for (const p of filteredProjects) {
				rows.push([
					p.short_id,
					p.name,
					p.client_name,
					p.status,
					p.services_count,
					p.total_value,
					p.total_invoiced,
					p.total_paid,
					p.balance_due
				]);
			}
		} else if (activeTab === 'clients') {
			rows.push([
				'Client Name',
				'Type',
				'Active Projects',
				'Services Count',
				'Total Invoiced',
				'Total Paid',
				'Total Due',
				'Advance Balance'
			]);
			for (const c of filteredClients) {
				rows.push([
					c.name,
					c.client_type,
					c.active_projects_count,
					c.total_services_count,
					c.total_invoiced,
					c.total_paid,
					c.total_due,
					c.advance_balance
				]);
			}
		}

		const csvContent =
			'data:text/csv;charset=utf-8,' +
			rows.map((e) => e.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(',')).join('\n');
		const encodedUri = encodeURI(csvContent);
		const link = document.createElement('a');
		link.setAttribute('href', encodedUri);
		link.setAttribute('download', filename);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	}
</script>

<svelte:head>
	<title>Company Reports & Analytics — ZenEngr</title>
</svelte:head>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-2xl font-bold tracking-tight text-slate-900">Company Reports & Analytics</h1>
			<p class="mt-1 text-sm text-slate-500">
				Executive performance, operational growth, and organization-wide financial intelligence.
			</p>
		</div>

		<div class="flex items-center gap-2.5">
			<button
				type="button"
				onclick={exportActiveTableToCsv}
				class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 focus:outline-hidden"
			>
				<Icon icon={download} class="h-4 w-4 text-slate-500" />
				Export CSV
			</button>
			<button
				type="button"
				onclick={resetFilters}
				class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 focus:outline-hidden"
				title="Reset to This Month"
			>
				<Icon icon={refresh} class="h-4 w-4 text-slate-500" />
				Reset
			</button>
		</div>
	</div>

	<!-- Filter & Date Range Hub -->
	<section
		class="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs sm:p-5"
		aria-label="Report Filters"
	>
		<!-- Date Preset Buttons -->
		<div class="flex items-center gap-1.5 overflow-x-auto pb-2 sm:pb-0">
			<span
				class="mr-1 hidden items-center gap-1 text-xs font-semibold text-slate-400 sm:inline-flex"
			>
				<Icon icon={calendarRange} class="h-4 w-4 text-slate-400" />
				Range:
			</span>
			{#each PRESETS as preset (preset.id)}
				<button
					type="button"
					onclick={() => selectPreset(preset.id)}
					class="shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all {selectedPreset ===
					preset.id
						? 'bg-indigo-600 text-white shadow-2xs'
						: 'bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900'}"
				>
					{preset.label}
				</button>
			{/each}
		</div>

		<!-- Custom Date & Entity Pickers Drawer -->
		<div
			class="mt-4 grid gap-3 border-t border-slate-100 pt-4 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-12"
		>
			{#if selectedPreset === 'custom'}
				<div class="sm:col-span-1 md:col-span-2 lg:col-span-3">
					<label for="rep-date-from" class="block text-xs font-medium text-slate-600"
						>From Date</label
					>
					<input
						type="date"
						id="rep-date-from"
						bind:value={customFrom}
						onchange={() => applyFilters('custom')}
						class="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
					/>
				</div>
				<div class="sm:col-span-1 md:col-span-2 lg:col-span-3">
					<label for="rep-date-to" class="block text-xs font-medium text-slate-600">To Date</label>
					<input
						type="date"
						id="rep-date-to"
						bind:value={customTo}
						onchange={() => applyFilters('custom')}
						class="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
					/>
				</div>
			{/if}

			<div class="sm:col-span-1 md:col-span-2 lg:col-span-3">
				<label for="rep-client-filter" class="block text-xs font-medium text-slate-600"
					>Filter by Client</label
				>
				<div class="mt-1">
					<ClientPicker
						id="rep-client-filter"
						bind:value={selectedClientId}
						onselect={(c) => {
							selectedClientId = c ? c.id : '';
							applyFilters();
						}}
						placeholder="All Clients"
					/>
				</div>
			</div>

			<div class="sm:col-span-1 md:col-span-2 lg:col-span-3">
				<label for="rep-proj-filter" class="block text-xs font-medium text-slate-600"
					>Filter by Project</label
				>
				<div class="mt-1">
					<ProjectPicker
						id="rep-proj-filter"
						bind:value={selectedProjectId}
						clientId={selectedClientId || undefined}
						onselect={(p) => {
							selectedProjectId = p ? p.id : '';
							applyFilters();
						}}
						placeholder="All Projects"
					/>
				</div>
			</div>

			<div class="sm:col-span-1 md:col-span-2 lg:col-span-3">
				<label for="rep-granularity" class="block text-xs font-medium text-slate-600"
					>Timeline Grouping</label
				>
				<select
					id="rep-granularity"
					bind:value={selectedGranularity}
					onchange={() => applyFilters()}
					class="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
				>
					<option value="month">Monthly Interval</option>
					<option value="day">Daily Interval</option>
				</select>
			</div>
		</div>
	</section>

	<!-- Executive KPI Summary Cards -->
	<section
		class="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7"
		aria-label="Executive KPI Summary"
	>
		<!-- 1. New Projects -->
		<div class="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
			<div class="flex items-center justify-between">
				<dt class="text-[11px] font-bold tracking-wider text-slate-500 uppercase">New Projects</dt>
				<Icon icon={folderMultiple} class="h-4 w-4 text-indigo-500" />
			</div>
			<dd class="mt-2 text-2xl font-bold text-slate-900">
				{data.ledgerData.summary.new_projects_count}
			</dd>
			<p class="mt-1 text-[11px] text-slate-400">Created in period</p>
		</div>

		<!-- 2. New Services -->
		<div class="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
			<div class="flex items-center justify-between">
				<dt class="text-[11px] font-bold tracking-wider text-slate-500 uppercase">New Services</dt>
				<Icon icon={cogBox} class="h-4 w-4 text-violet-500" />
			</div>
			<dd class="mt-2 text-2xl font-bold text-slate-900">
				{data.ledgerData.summary.new_services_count}
			</dd>
			<p class="mt-1 truncate text-[11px] font-medium text-violet-600">
				{fmtPrice(data.ledgerData.summary.new_services_value)} value
			</p>
		</div>

		<!-- 3. New Clients -->
		<div class="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
			<div class="flex items-center justify-between">
				<dt class="text-[11px] font-bold tracking-wider text-slate-500 uppercase">New Clients</dt>
				<Icon icon={accountMultiple} class="h-4 w-4 text-cyan-500" />
			</div>
			<dd class="mt-2 text-2xl font-bold text-slate-900">
				{data.ledgerData.summary.new_clients_count}
			</dd>
			<p class="mt-1 text-[11px] text-slate-400">Onboarded in period</p>
		</div>

		<!-- 4. Total Invoiced -->
		<div class="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
			<div class="flex items-center justify-between">
				<dt class="text-[11px] font-bold tracking-wider text-slate-500 uppercase">
					Total Invoiced
				</dt>
				<Icon icon={receiptText} class="h-4 w-4 text-slate-500" />
			</div>
			<dd class="mt-2 truncate text-xl font-bold text-slate-900">
				{fmtPrice(data.ledgerData.summary.total_invoiced)}
			</dd>
			<p class="mt-1 text-[11px] text-slate-400">Issued bills</p>
		</div>

		<!-- 5. Payments Collected -->
		<div class="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4 shadow-2xs">
			<div class="flex items-center justify-between">
				<dt class="text-[11px] font-bold tracking-wider text-emerald-800 uppercase">Collected</dt>
				<Icon icon={cashMultiple} class="h-4 w-4 text-emerald-600" />
			</div>
			<dd class="mt-2 truncate text-xl font-bold text-emerald-700">
				{fmtPrice(data.ledgerData.summary.total_collected)}
			</dd>
			<p class="mt-1 text-[11px] font-medium text-emerald-600">Net payments</p>
		</div>

		<!-- 6. Outstanding Due -->
		<div
			class="rounded-xl border p-4 shadow-2xs {Number(data.ledgerData.summary.total_due) > 0
				? 'border-amber-200 bg-amber-50/60'
				: 'border-slate-200 bg-white'}"
		>
			<div class="flex items-center justify-between">
				<dt
					class="text-[11px] font-bold tracking-wider {Number(data.ledgerData.summary.total_due) > 0
						? 'text-amber-800'
						: 'text-slate-500'} uppercase"
				>
					Outstanding Due
				</dt>
				<Icon
					icon={alertCircleOutline}
					class="h-4 w-4 {Number(data.ledgerData.summary.total_due) > 0
						? 'text-amber-600'
						: 'text-slate-400'}"
				/>
			</div>
			<dd
				class="mt-2 text-xl font-bold {Number(data.ledgerData.summary.total_due) > 0
					? 'text-amber-800'
					: 'text-slate-900'} truncate"
			>
				{fmtPrice(data.ledgerData.summary.total_due)}
			</dd>
			<p class="mt-1 text-[11px] text-slate-400">Total receivables</p>
		</div>

		<!-- 7. Advance Credits Held -->
		<div class="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 shadow-2xs">
			<div class="flex items-center justify-between">
				<dt class="text-[11px] font-bold tracking-wider text-indigo-800 uppercase">
					Advance Credits
				</dt>
				<Icon icon={walletOutline} class="h-4 w-4 text-indigo-600" />
			</div>
			<dd class="mt-2 truncate text-xl font-bold text-indigo-900">
				{fmtPrice(data.ledgerData.summary.total_advance_balance)}
			</dd>
			<p class="mt-1 text-[11px] text-indigo-600">Unused deposits</p>
		</div>
	</section>

	<!-- Multi-Dimensional Tabbed Analysis -->
	<div class="rounded-xl border border-slate-200 bg-white shadow-2xs">
		<!-- Tabs Navigation Header -->
		<div class="flex items-center justify-between border-b border-slate-200 px-4 pt-3 sm:px-6">
			<nav class="-mb-px flex space-x-6" aria-label="Report Views">
				<button
					type="button"
					onclick={() => (activeTab = 'timeline')}
					class="border-b-2 py-3 text-xs font-semibold whitespace-nowrap transition-all {activeTab ===
					'timeline'
						? 'border-indigo-600 text-indigo-600'
						: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
				>
					Timeline ({data.ledgerData.timeline.length} periods)
				</button>
				<button
					type="button"
					onclick={() => (activeTab = 'projects')}
					class="border-b-2 py-3 text-xs font-semibold whitespace-nowrap transition-all {activeTab ===
					'projects'
						? 'border-indigo-600 text-indigo-600'
						: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
				>
					Project Breakdown ({data.ledgerData.projects.length})
				</button>
				<button
					type="button"
					onclick={() => (activeTab = 'clients')}
					class="border-b-2 py-3 text-xs font-semibold whitespace-nowrap transition-all {activeTab ===
					'clients'
						? 'border-indigo-600 text-indigo-600'
						: 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'}"
				>
					Client Breakdown ({data.ledgerData.clients.length})
				</button>
			</nav>
		</div>

		<!-- Tab 1: Timeline -->
		{#if activeTab === 'timeline'}
			<div class="p-4 sm:p-6">
				{#if data.ledgerData.timeline.length === 0}
					<div class="py-12 text-center">
						<p class="text-sm font-medium text-slate-500">
							No financial or operational activity in the selected date window.
						</p>
					</div>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-left text-xs">
							<thead>
								<tr class="border-b border-slate-200 text-slate-500">
									<th class="py-2.5 font-semibold">Period</th>
									<th class="py-2.5 text-center font-semibold">New Proj</th>
									<th class="py-2.5 text-center font-semibold">New Clients</th>
									<th class="py-2.5 text-center font-semibold">New Services</th>
									<th class="py-2.5 text-right font-semibold">Invoiced</th>
									<th class="py-2.5 text-right font-semibold">Collected</th>
									<th class="py-2.5 text-right font-semibold">Net Movement</th>
									<th class="w-48 py-2.5 pl-6 font-semibold">Volume Comparison</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-100">
								{#each data.ledgerData.timeline as item (item.period)}
									{@const invNum = Number(item.invoiced_amount) || 0}
									{@const collNum = Number(item.collected_amount) || 0}
									{@const netNum = Number(item.net_due_change) || 0}
									<tr class="hover:bg-slate-50/70">
										<td class="py-3 font-semibold text-slate-900">{item.period_label}</td>
										<td class="py-3 text-center text-slate-700">{item.new_projects}</td>
										<td class="py-3 text-center text-slate-700">{item.new_clients}</td>
										<td class="py-3 text-center text-slate-700">{item.new_services}</td>
										<td class="py-3 text-right font-medium text-slate-900">
											{fmtPrice(item.invoiced_amount)}
										</td>
										<td class="py-3 text-right font-semibold text-emerald-600">
											{fmtPrice(item.collected_amount)}
										</td>
										<td
											class="py-3 text-right font-semibold {netNum > 0
												? 'text-amber-700'
												: netNum < 0
													? 'text-emerald-700'
													: 'text-slate-400'}"
										>
											{netNum > 0 ? '+' : ''}{fmtPrice(item.net_due_change)}
										</td>
										<td class="py-3 pl-6">
											<div class="flex items-center gap-1.5 text-[10px]">
												<div class="flex h-2 w-full overflow-hidden rounded-full bg-slate-100">
													<div
														class="h-full bg-slate-400"
														style="width: {Math.min(100, (invNum / maxTimelineVolume) * 100)}%"
														title="Invoiced: {fmtPrice(invNum)}"
													></div>
													<div
														class="-ml-1 h-full bg-emerald-500 opacity-90"
														style="width: {Math.min(100, (collNum / maxTimelineVolume) * 100)}%"
														title="Collected: {fmtPrice(collNum)}"
													></div>
												</div>
											</div>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Tab 2: Projects Breakdown -->
		{#if activeTab === 'projects'}
			<div class="space-y-4 p-4 sm:p-6">
				<!-- Search and Sort Bar -->
				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<div class="relative w-full max-w-sm">
						<Icon
							icon={magnify}
							class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400"
						/>
						<input
							type="text"
							bind:value={projectSearch}
							placeholder="Search by project name, ID, or client..."
							class="w-full rounded-lg border border-slate-200 bg-white py-1.5 pr-3 pl-9 text-xs text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
						/>
					</div>

					<div class="flex items-center gap-2">
						<label for="rep-proj-sort" class="text-xs font-medium text-slate-500">Sort by:</label>
						<select
							id="rep-proj-sort"
							bind:value={projectSort}
							class="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
						>
							<option value="due_desc">Highest Due First</option>
							<option value="invoiced_desc">Highest Invoiced First</option>
							<option value="name_asc">Project Name (A-Z)</option>
						</select>
					</div>
				</div>

				<!-- Projects Table -->
				{#if filteredProjects.length === 0}
					<div class="py-12 text-center">
						<p class="text-sm font-medium text-slate-500">No matching projects found.</p>
					</div>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-left text-xs">
							<thead>
								<tr class="border-b border-slate-200 text-slate-500">
									<th class="py-2.5 font-semibold">Project</th>
									<th class="py-2.5 font-semibold">Client</th>
									<th class="py-2.5 font-semibold">Status</th>
									<th class="py-2.5 text-center font-semibold">Services</th>
									<th class="py-2.5 text-right font-semibold">Total Value</th>
									<th class="py-2.5 text-right font-semibold">Invoiced</th>
									<th class="py-2.5 text-right font-semibold">Paid</th>
									<th class="py-2.5 text-right font-semibold">Balance Due</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-100">
								{#each filteredProjects as proj (proj.project_id)}
									{@const dueNum = Number(proj.balance_due) || 0}
									<tr class="hover:bg-slate-50/70">
										<td class="py-3">
											<a
												href={resolve(`/app/projects/${proj.project_id}`)}
												class="font-semibold text-slate-900 hover:text-indigo-600 hover:underline"
											>
												{proj.name}
											</a>
											<span
												class="ml-1.5 inline-flex items-center rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600"
											>
												{proj.short_id}
											</span>
										</td>
										<td class="py-3 text-slate-600">
											<a
												href={resolve(`/app/clients/${proj.client_id}`)}
												class="hover:text-indigo-600 hover:underline"
											>
												{proj.client_name}
											</a>
										</td>
										<td class="py-3">
											<StatusBadge status={proj.status} />
										</td>
										<td class="py-3 text-center text-slate-700">{proj.services_count}</td>
										<td class="py-3 text-right text-slate-800">{fmtPrice(proj.total_value)}</td>
										<td class="py-3 text-right text-slate-800">{fmtPrice(proj.total_invoiced)}</td>
										<td class="py-3 text-right font-medium text-emerald-600">
											{fmtPrice(proj.total_paid)}
										</td>
										<td
											class="py-3 text-right font-bold {dueNum > 0
												? 'text-amber-800'
												: 'text-slate-400'}"
										>
											{fmtPrice(proj.balance_due)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Tab 3: Clients Breakdown -->
		{#if activeTab === 'clients'}
			<div class="space-y-4 p-4 sm:p-6">
				<!-- Search and Sort Bar -->
				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<div class="relative w-full max-w-sm">
						<Icon
							icon={magnify}
							class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400"
						/>
						<input
							type="text"
							bind:value={clientSearch}
							placeholder="Search by client name..."
							class="w-full rounded-lg border border-slate-200 bg-white py-1.5 pr-3 pl-9 text-xs text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
						/>
					</div>

					<div class="flex items-center gap-2">
						<label for="rep-cli-sort" class="text-xs font-medium text-slate-500">Sort by:</label>
						<select
							id="rep-cli-sort"
							bind:value={clientSort}
							class="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
						>
							<option value="due_desc">Highest Due First</option>
							<option value="invoiced_desc">Highest Invoiced First</option>
							<option value="name_asc">Client Name (A-Z)</option>
						</select>
					</div>
				</div>

				<!-- Clients Table -->
				{#if filteredClients.length === 0}
					<div class="py-12 text-center">
						<p class="text-sm font-medium text-slate-500">No matching clients found.</p>
					</div>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-left text-xs">
							<thead>
								<tr class="border-b border-slate-200 text-slate-500">
									<th class="py-2.5 font-semibold">Client Name</th>
									<th class="py-2.5 font-semibold">Type</th>
									<th class="py-2.5 text-center font-semibold">Projects</th>
									<th class="py-2.5 text-center font-semibold">Services</th>
									<th class="py-2.5 text-right font-semibold">Total Invoiced</th>
									<th class="py-2.5 text-right font-semibold">Total Paid</th>
									<th class="py-2.5 text-right font-semibold">Outstanding Due</th>
									<th class="py-2.5 text-right font-semibold">Advance Credit</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-100">
								{#each filteredClients as client (client.client_id)}
									{@const dueNum = Number(client.total_due) || 0}
									{@const advNum = Number(client.advance_balance) || 0}
									<tr class="hover:bg-slate-50/70">
										<td class="py-3">
											<a
												href={resolve(`/app/clients/${client.client_id}`)}
												class="font-semibold text-slate-900 hover:text-indigo-600 hover:underline"
											>
												{client.name}
											</a>
										</td>
										<td class="py-3 text-slate-500 capitalize">{client.client_type}</td>
										<td class="py-3 text-center text-slate-700">{client.active_projects_count}</td>
										<td class="py-3 text-center text-slate-700">{client.total_services_count}</td>
										<td class="py-3 text-right text-slate-800">{fmtPrice(client.total_invoiced)}</td
										>
										<td class="py-3 text-right font-medium text-emerald-600">
											{fmtPrice(client.total_paid)}
										</td>
										<td
											class="py-3 text-right font-bold {dueNum > 0
												? 'text-amber-800'
												: 'text-slate-400'}"
										>
											{fmtPrice(client.total_due)}
										</td>
										<td
											class="py-3 text-right font-semibold {advNum > 0
												? 'text-indigo-600'
												: 'text-slate-400'}"
										>
											{fmtPrice(client.advance_balance)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
