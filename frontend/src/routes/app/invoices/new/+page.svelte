<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Icon from '@iconify/svelte';
	import trashCanOutline from '@iconify-icons/mdi/trash-can-outline';
	import plus from '@iconify-icons/mdi/plus';
	import briefcaseOutline from '@iconify-icons/mdi/briefcase-outline';
	import fileDocumentOutline from '@iconify-icons/mdi/file-document-outline';
	import magnify from '@iconify-icons/mdi/magnify';
	import close from '@iconify-icons/mdi/close';
	import check from '@iconify-icons/mdi/check';
	import { ApiError } from '$lib/api/client.js';
	import * as invoiceApi from '$lib/api/invoices.js';
	import * as projectApi from '$lib/api/projects.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { fmtPrice } from '$lib/utils/format.js';

	let { data } = $props();

	const token = auth.token;

	// Invoice Type: 'project' | 'general'
	let invoiceType = $state(untrack(() => (data.initialProjectId ? 'project' : 'project')));
	let projectId = $state(untrack(() => data.initialProjectId));

	// Searchable Project Picker
	let projectSearchQuery = $state('');
	let projectDropdownOpen = $state(false);

	// Billed To info for General Invoices
	let billedTo = $state({
		name: '',
		email: '',
		phone: '',
		address: '',
		tax_id: ''
	});
	let selectedClientId = $state('');

	let issueDate = $state(null);
	let dueDate = $state(null);
	let notes = $state('');
	let projectServices = $state([]);
	let loadedProjectId = $state(null);
	let servicesLoading = $state(false);
	let servicesErr = $state(null);
	let projectLedger = $state(null);

	let rowKey = 1;
	const today = new Date().toISOString().slice(0, 10);
	let rows = $state([]);
	let busy = $state(false);
	let err = $state(null);

	$effect(() => {
		if (invoiceType === 'project' && projectId && projectId !== loadedProjectId) {
			loadServices();
		} else if (invoiceType === 'general' || !projectId) {
			projectServices = [];
			projectLedger = null;
		}
	});

	async function loadServices() {
		servicesLoading = true;
		servicesErr = null;
		try {
			const [project, ledger] = await Promise.all([
				projectApi.getProject(fetch, token, projectId),
				projectApi.getProjectLedger(fetch, token, projectId).catch(() => null)
			]);
			projectServices = project.services.filter((s) => s.status === 'active');
			projectLedger = ledger;
			loadedProjectId = projectId;
			rows = [];
		} catch (e) {
			servicesErr = e instanceof ApiError ? e.message : 'Could not load project services.';
		} finally {
			servicesLoading = false;
		}
	}

	function switchType(newType) {
		if (invoiceType === newType) return;
		invoiceType = newType;
		err = null;
		if (newType === 'general') {
			projectId = '';
			loadedProjectId = null;
			projectServices = [];
			projectLedger = null;
			// Convert all rows to custom
			rows = rows.map((r) => ({
				...r,
				kind: 'custom',
				project_service_id: '',
				service_name: ''
			}));
		} else {
			// Switch back to project: clear general billed-to prefill
			selectedClientId = '';
		}
	}

	function onClientSelect(clientId) {
		selectedClientId = clientId;
		if (!clientId) return;
		const client = data.clients.find((c) => c.id === clientId);
		if (client) {
			billedTo.name = client.name || '';
			billedTo.email = client.email || '';
			billedTo.phone = client.phone || '';
			billedTo.tax_id = client.tax_id || '';
			if (client.billing_address) {
				if (typeof client.billing_address === 'string') {
					billedTo.address = client.billing_address;
				} else if (typeof client.billing_address === 'object') {
					const parts = [
						client.billing_address.street,
						client.billing_address.city,
						client.billing_address.state,
						client.billing_address.postal_code,
						client.billing_address.country
					].filter(Boolean);
					billedTo.address = parts.join(', ');
				}
			}
		}
	}

	// Filtered projects for searchable combobox
	let filteredProjects = $derived.by(() => {
		const q = projectSearchQuery.trim().toLowerCase();
		if (!q) return data.projects;
		return data.projects.filter(
			(p) =>
				p.name?.toLowerCase().includes(q) ||
				p.client_name?.toLowerCase().includes(q) ||
				p.client?.name?.toLowerCase().includes(q)
		);
	});

	let selectedProject = $derived(data.projects.find((p) => p.id === projectId));

	function selectProject(proj) {
		projectId = proj.id;
		projectSearchQuery = '';
		projectDropdownOpen = false;
	}

	function clearSelectedProject() {
		projectId = '';
		loadedProjectId = null;
		projectServices = [];
		rows = [];
		projectLedger = null;
	}

	function addRow() {
		rows.push({
			key: rowKey++,
			kind: invoiceType === 'project' && projectId ? 'service' : 'custom',
			project_service_id: '',
			service_name: '',
			unit_price: '',
			quantity: 1,
			description: '',
			entry_date: today
		});
	}

	function removeRow(key) {
		rows = rows.filter((r) => r.key !== key);
	}

	function onRowServiceChange(row, psId) {
		row.project_service_id = psId;
		const ps = projectServices.find((s) => s.id === psId);
		row.service_name = ps?.service_name ?? '';
		row.unit_price = ps?.price_at_attachment ?? '';
	}

	let subtotal = $derived.by(() =>
		rows.reduce((sum, r) => sum + r.quantity * (Number(r.unit_price) || 0), 0)
	);

	let invoicedByService = $derived.by(() => {
		const map = {};
		for (const e of projectLedger?.entries ?? []) {
			if (
				e.type !== 'charge' ||
				!e.invoice_number ||
				e.source_type !== 'project_service' ||
				!e.source_id
			) {
				continue;
			}
			(map[e.source_id] ??= []).push(e.invoice_number);
		}
		for (const k of Object.keys(map)) map[k] = [...new Set(map[k])];
		return map;
	});

	function invoicedFlag(psId) {
		const nums = invoicedByService[psId];
		if (!nums || nums.length === 0) return null;
		const head = nums[0];
		return nums.length > 1 ? `Invoiced — ${head} +${nums.length - 1} more` : `Invoiced — ${head}`;
	}

	let discount = $derived.by(() => {
		const s = projectLedger?.summary;
		if (!s) return null;
		const type = s.discount_type;
		if (type !== 'percentage' && type !== 'fixed') return null;
		if (!(subtotal > 0)) return null;
		const v = Number(s.discount_value) || 0;
		if (!(v > 0)) return null;
		const amount =
			type === 'percentage' ? Math.round(subtotal * (v / 100) * 100) / 100 : Math.min(v, subtotal);
		if (!(amount > 0)) return null;
		return { amount, label: `Discount (${type} ${s.discount_value})` };
	});

	let total = $derived(subtotal - (discount?.amount ?? 0));

	async function submit() {
		err = null;
		if (invoiceType === 'project' && !projectId) {
			err = 'Please select a project for the invoice.';
			return;
		}
		if (invoiceType === 'general' && !billedTo.name.trim()) {
			err = 'Please provide a recipient or company name in Billed To info.';
			return;
		}
		if (rows.length === 0) {
			err = 'Add at least one line item.';
			return;
		}
		for (const r of rows) {
			if (invoiceType === 'general' && r.kind === 'service') {
				r.kind = 'custom';
			}
			if (r.kind === 'service' && !r.project_service_id) {
				err = 'Every service line item needs a service selected.';
				return;
			}
			if (r.kind === 'custom') {
				if (!r.description.trim()) {
					err = 'Every custom line item needs a description.';
					return;
				}
				if (r.unit_price === '' || Number(r.unit_price) < 0) {
					err = 'Every custom line item needs a valid unit price.';
					return;
				}
			}
		}
		busy = true;
		try {
			const body = {
				line_items: rows.map((r) => {
					const item = {};
					if (r.entry_date) item.entry_date = r.entry_date;
					if (r.kind === 'service') {
						item.project_service_id = r.project_service_id;
					} else {
						item.description = r.description.trim();
						item.unit_price = String(r.unit_price);
						item.quantity = r.quantity || 1;
					}
					return item;
				})
			};
			if (discount) {
				body.line_items.push({
					description: discount.label,
					unit_price: String(-discount.amount),
					quantity: 1
				});
			}
			if (invoiceType === 'project' && projectId) {
				body.project_id = projectId;
			}
			if (invoiceType === 'general') {
				body.billed_to = {
					name: billedTo.name.trim(),
					email: billedTo.email.trim(),
					phone: billedTo.phone.trim(),
					address: billedTo.address.trim(),
					tax_id: billedTo.tax_id.trim()
				};
			}
			if (issueDate) body.issue_date = issueDate;
			if (dueDate) body.due_date = dueDate;
			if (notes.trim()) body.notes = notes.trim();

			const created = await invoiceApi.createInvoice(fetch, token, body);
			goto(resolve('/app/invoices/[id]', { id: created.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Create invoice failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>New invoice — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex flex-wrap items-center gap-1">
		<li>
			<a href={resolve('/app/invoices')} class="hover:text-indigo-600">Invoices</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">New</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">New invoice</h1>
		<p class="mt-1 text-sm text-slate-500">
			Create a formal project invoice or a general billing invoice.
		</p>
	</div>
</div>

{#if err}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{err}
	</p>
{/if}

<form
	class="mt-6 w-full space-y-6"
	onsubmit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<!-- ══════════════════════════════════════════════════════════════ -->
	<!-- 1. Invoice Type Selector Segmented Control -->
	<!-- ══════════════════════════════════════════════════════════════ -->
	<section
		class="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs"
		aria-labelledby="type-selector-h"
	>
		<div class="flex items-center justify-between">
			<div>
				<h2 id="type-selector-h" class="text-sm font-bold text-slate-900">Invoice Type *</h2>
				<p class="text-xs text-slate-500">
					Select whether this invoice is for a specific client project or general billing.
				</p>
			</div>
		</div>

		<div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
			<!-- Project Invoice Option Card -->
			<button
				type="button"
				onclick={() => switchType('project')}
				class="flex items-start gap-3 rounded-xl border p-3.5 text-left transition-all {invoiceType ===
				'project'
					? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20'
					: 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/70'}"
			>
				<div
					class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg {invoiceType ===
					'project'
						? 'bg-indigo-600 text-white'
						: 'bg-slate-100 text-slate-500'}"
				>
					<Icon icon={briefcaseOutline} class="h-5 w-5" />
				</div>
				<div class="min-w-0 flex-1">
					<div class="flex items-center justify-between gap-2">
						<span class="text-sm font-semibold text-slate-900">Project Invoice</span>
						{#if invoiceType === 'project'}
							<span
								class="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-700"
							>
								<Icon icon={check} class="h-3 w-3" /> Selected
							</span>
						{/if}
					</div>
					<p class="mt-0.5 text-xs text-slate-500">
						Attach active project services, track milestones, and apply project-level discounts.
					</p>
				</div>
			</button>

			<!-- General Invoice Option Card -->
			<button
				type="button"
				onclick={() => switchType('general')}
				class="flex items-start gap-3 rounded-xl border p-3.5 text-left transition-all {invoiceType ===
				'general'
					? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20'
					: 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/70'}"
			>
				<div
					class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg {invoiceType ===
					'general'
						? 'bg-indigo-600 text-white'
						: 'bg-slate-100 text-slate-500'}"
				>
					<Icon icon={fileDocumentOutline} class="h-5 w-5" />
				</div>
				<div class="min-w-0 flex-1">
					<div class="flex items-center justify-between gap-2">
						<span class="text-sm font-semibold text-slate-900">General Invoice</span>
						{#if invoiceType === 'general'}
							<span
								class="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-700"
							>
								<Icon icon={check} class="h-3 w-3" /> Selected
							</span>
						{/if}
					</div>
					<p class="mt-0.5 text-xs text-slate-500">
						Ad-hoc or internal billing with custom line items and customizable Billed-To info.
					</p>
				</div>
			</button>
		</div>
	</section>

	<!-- ══════════════════════════════════════════════════════════════ -->
	<!-- 2A. Project Selection (when Project Invoice is selected) -->
	<!-- ══════════════════════════════════════════════════════════════ -->
	{#if invoiceType === 'project'}
		<section class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
			<div>
				<label for="search-project-input" class="block text-sm font-bold text-slate-900">
					Select Project *
				</label>
				<p class="text-xs text-slate-500">
					Search and pick a project to pull in billable services and client details.
				</p>
			</div>

			{#if selectedProject}
				<!-- Selected Project Card -->
				<div
					class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-indigo-200 bg-indigo-50/60 p-4"
				>
					<div class="flex items-center gap-3 min-w-0">
						<div
							class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white"
						>
							<Icon icon={briefcaseOutline} class="h-5 w-5" />
						</div>
						<div class="min-w-0">
							<div class="flex items-center gap-2">
								<span class="text-sm font-bold text-slate-900 truncate">
									{selectedProject.name}
								</span>
								<StatusBadge status={selectedProject.status} />
							</div>
							<p class="mt-0.5 text-xs text-slate-500">
								Client: <span class="font-medium text-slate-700"
									>{selectedProject.client_name ||
										selectedProject.client?.name ||
										'Direct Client'}</span
								>
							</p>
						</div>
					</div>

					<div class="flex items-center gap-2">
						<button
							type="button"
							onclick={() => {
								projectDropdownOpen = true;
							}}
							class="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500"
						>
							Change project
						</button>
						<button
							type="button"
							onclick={clearSelectedProject}
							title="Clear selection"
							class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-400 shadow-2xs hover:border-red-300 hover:bg-red-50 hover:text-red-600 focus-visible:ring-2 focus-visible:ring-red-500"
						>
							<Icon icon={close} class="h-4 w-4" />
						</button>
					</div>
				</div>
			{/if}

			<!-- Searchable Input & Dropdown Picker -->
			{#if !selectedProject || projectDropdownOpen}
				<div class="relative">
					<div class="relative">
						<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
							<Icon icon={magnify} class="h-4 w-4 text-slate-400" />
						</div>
						<input
							id="search-project-input"
							type="text"
							bind:value={projectSearchQuery}
							onfocus={() => (projectDropdownOpen = true)}
							placeholder="Search project by name or client..."
							class="block w-full rounded-lg border-slate-300 pl-9 pr-8 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
						{#if projectSearchQuery}
							<button
								type="button"
								onclick={() => (projectSearchQuery = '')}
								class="absolute inset-y-0 right-0 flex items-center pr-2.5 text-slate-400 hover:text-slate-600"
							>
								<Icon icon={close} class="h-4 w-4" />
							</button>
						{/if}
					</div>

					<!-- Dropdown Results -->
					{#if projectDropdownOpen}
						<div
							class="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-lg ring-1 ring-black/5"
						>
							{#if filteredProjects.length === 0}
								<div class="p-3 text-center text-xs text-slate-500">
									No projects found matching "{projectSearchQuery}".
								</div>
							{:else}
								{#each filteredProjects as p (p.id)}
									<button
										type="button"
										onclick={() => selectProject(p)}
										class="flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left text-xs transition-colors hover:bg-indigo-50/60 {p.id ===
										projectId
											? 'bg-indigo-50 font-semibold text-indigo-900'
											: 'text-slate-700'}"
									>
										<div class="min-w-0 flex-1">
											<div class="flex items-center gap-2">
												<span class="font-medium text-slate-900 truncate">{p.name}</span>
												<StatusBadge status={p.status} />
											</div>
											<div class="mt-0.5 text-[11px] text-slate-500">
												Client: {p.client_name || p.client?.name || '—'}
											</div>
										</div>
										{#if p.id === projectId}
											<Icon icon={check} class="h-4 w-4 text-indigo-600 shrink-0" />
										{/if}
									</button>
								{/each}
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		</section>

		<!-- ══════════════════════════════════════════════════════════════ -->
		<!-- 2B. Billed To Information (when General Invoice is selected) -->
		<!-- ══════════════════════════════════════════════════════════════ -->
	{:else}
		<section
			class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4"
			aria-labelledby="billed-to-h"
		>
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div>
					<h2 id="billed-to-h" class="text-sm font-bold text-slate-900">Billed To Information *</h2>
					<p class="text-xs text-slate-500">
						Provide recipient details for this invoice, or select an existing client to auto-fill.
					</p>
				</div>

				<!-- Quick client auto-fill -->
				{#if data.clients && data.clients.length > 0}
					<div class="flex items-center gap-2">
						<label for="quick-client" class="text-xs font-semibold text-slate-600">
							Auto-fill from client:
						</label>
						<select
							id="quick-client"
							value={selectedClientId}
							onchange={(e) => onClientSelect(e.currentTarget.value)}
							class="rounded-lg border-slate-300 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 py-1.5"
						>
							<option value="">— Select a client to pre-fill —</option>
							{#each data.clients as c (c.id)}
								<option value={c.id}>{c.name}</option>
							{/each}
						</select>
					</div>
				{/if}
			</div>

			<div class="grid gap-4 sm:grid-cols-2">
				<div class="sm:col-span-2">
					<label for="bt-name" class="block text-xs font-semibold text-slate-700">
						Client / Recipient Name *
					</label>
					<input
						id="bt-name"
						type="text"
						bind:value={billedTo.name}
						placeholder="e.g. Acme Corporation or Jane Doe"
						class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div>
					<label for="bt-email" class="block text-xs font-semibold text-slate-700">
						Billing Email
					</label>
					<input
						id="bt-email"
						type="email"
						bind:value={billedTo.email}
						placeholder="billing@example.com"
						class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div>
					<label for="bt-phone" class="block text-xs font-semibold text-slate-700">
						Phone Number
					</label>
					<input
						id="bt-phone"
						type="tel"
						bind:value={billedTo.phone}
						placeholder="+1 (555) 000-0000"
						class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div class="sm:col-span-2">
					<label for="bt-address" class="block text-xs font-semibold text-slate-700">
						Billing Address
					</label>
					<textarea
						id="bt-address"
						bind:value={billedTo.address}
						rows="2"
						placeholder="Street address, City, State/Province, Postal code, Country"
						class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					></textarea>
				</div>

				<div>
					<label for="bt-tax" class="block text-xs font-semibold text-slate-700">
						Tax ID / VAT Number
					</label>
					<input
						id="bt-tax"
						type="text"
						bind:value={billedTo.tax_id}
						placeholder="e.g. VAT12345678"
						class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
		</section>
	{/if}

	<!-- ══════════════════════════════════════════════════════════════ -->
	<!-- 3. Dates & Notes Section -->
	<!-- ══════════════════════════════════════════════════════════════ -->
	<section class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
		<h2 class="text-sm font-bold text-slate-900">Dates & Terms</h2>
		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<label for="i-issue" class="block text-xs font-semibold text-slate-700">Issue Date</label>
				<input
					id="i-issue"
					type="date"
					bind:value={issueDate}
					class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="i-due" class="block text-xs font-semibold text-slate-700">Due Date</label>
				<input
					id="i-due"
					type="date"
					bind:value={dueDate}
					class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
		</div>

		<div>
			<label for="i-notes" class="block text-xs font-semibold text-slate-700">Notes / Memo</label>
			<textarea
				id="i-notes"
				bind:value={notes}
				rows="3"
				placeholder="Payment terms, wire instructions, or notes for the recipient..."
				class="mt-1 block w-full rounded-lg border-slate-300 px-3 py-2 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
			></textarea>
		</div>
	</section>

	<!-- ══════════════════════════════════════════════════════════════ -->
	<!-- 4. Line Items Section -->
	<!-- ══════════════════════════════════════════════════════════════ -->
	<section
		class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs"
		aria-labelledby="line-items-h"
	>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h2 id="line-items-h" class="text-sm font-bold text-slate-900">Line Items *</h2>
				<p class="mt-0.5 text-xs text-slate-500">
					{#if invoiceType === 'project'}
						Pick a project service to bill at its attached price, or add custom line items.
					{:else}
						Add custom billable items, services, or consultancy lines.
					{/if}
				</p>
			</div>
			<button
				type="button"
				onclick={addRow}
				class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				<Icon icon={plus} class="h-3.5 w-3.5" />
				Add Item
			</button>
		</div>

		{#if servicesErr}
			<p
				role="alert"
				class="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800"
			>
				{servicesErr}
			</p>
		{/if}

		{#if invoiceType === 'project' && projectId && servicesLoading}
			<div class="mt-3 flex items-center gap-2 text-xs text-slate-600">
				<Spinner class="h-3.5 w-3.5 text-indigo-600" /> Loading project services…
			</div>
		{:else if invoiceType === 'project' && projectId && projectServices.length === 0}
			<p class="mt-3 text-xs text-slate-500">
				This project has no active services. Add custom lines instead, or attach services on the
				project page.
			</p>
		{/if}

		{#if rows.length === 0}
			<div class="mt-4 rounded-xl border border-dashed border-slate-300 p-6 text-center">
				<p class="text-xs text-slate-500">No line items added yet.</p>
				<button
					type="button"
					onclick={addRow}
					class="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-indigo-600 shadow-2xs hover:bg-indigo-50"
				>
					<Icon icon={plus} class="h-3.5 w-3.5" />
					Add first item
				</button>
			</div>
		{/if}

		<div class="mt-4 space-y-2.5">
			{#each rows as row (row.key)}
				{@const amount = row.quantity * (Number(row.unit_price) || 0)}
				<div
					class="rounded-xl border border-slate-200 bg-slate-50/70 p-3 transition-colors hover:border-slate-300"
				>
					<div class="flex flex-wrap items-end gap-2.5 lg:flex-nowrap">
						<!-- Date -->
						<div class="w-full shrink-0 sm:w-32">
							<label
								for={`li-date-${row.key}`}
								class="mb-1 block text-[11px] font-semibold text-slate-600"
							>
								Date
							</label>
							<input
								id={`li-date-${row.key}`}
								type="date"
								bind:value={row.entry_date}
								class="block w-full rounded-lg border-slate-300 px-2.5 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>

						<!-- Type Selector on Row -->
						{#if invoiceType === 'project' && projectId}
							<div class="w-full shrink-0 sm:w-28">
								<label
									for={`li-kind-${row.key}`}
									class="mb-1 block text-[11px] font-semibold text-slate-600"
								>
									Type
								</label>
								<select
									id={`li-kind-${row.key}`}
									bind:value={row.kind}
									class="block w-full rounded-lg border-slate-300 px-2.5 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
								>
									<option value="service">Service</option>
									<option value="custom">Custom</option>
								</select>
							</div>
						{/if}

						<!-- Service Select or Description Input -->
						{#if row.kind === 'service' && invoiceType === 'project'}
							<div class="min-w-[180px] flex-1">
								<label
									for={`li-service-${row.key}`}
									class="mb-1 block text-[11px] font-semibold text-slate-600"
								>
									Project Service *
								</label>
								<select
									id={`li-service-${row.key}`}
									value={row.project_service_id}
									onchange={(e) => onRowServiceChange(row, e.currentTarget.value)}
									class="block w-full rounded-lg border-slate-300 px-2.5 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
								>
									<option value="" disabled>Select a service</option>
									{#each projectServices as ps (ps.id)}
										{@const flag = invoicedFlag(ps.id)}
										<option value={ps.id}>
											{ps.service_name}{flag ? ` — ${flag}` : ''}
										</option>
									{/each}
								</select>
							</div>
							<div class="w-28 shrink-0">
								<span class="mb-1 block text-[11px] font-semibold text-slate-600">Unit Price</span>
								<div
									class="flex h-[34px] items-center rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-700"
								>
									{row.unit_price === '' ? '—' : fmtPrice(row.unit_price)}
								</div>
							</div>
						{:else}
							<div class="min-w-[180px] flex-1">
								<label
									for={`li-desc-${row.key}`}
									class="mb-1 block text-[11px] font-semibold text-slate-600"
								>
									Description *
								</label>
								<input
									id={`li-desc-${row.key}`}
									type="text"
									bind:value={row.description}
									placeholder="e.g. Consulting, Design, Engineering"
									class="block w-full rounded-lg border-slate-300 px-2.5 py-1.5 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
								/>
							</div>
							<div class="w-28 shrink-0">
								<label
									for={`li-price-${row.key}`}
									class="mb-1 block text-[11px] font-semibold text-slate-600"
								>
									Unit Price *
								</label>
								<input
									id={`li-price-${row.key}`}
									type="number"
									min="0"
									step="0.01"
									bind:value={row.unit_price}
									placeholder="0.00"
									class="block w-full rounded-lg border-slate-300 px-2.5 py-1.5 font-mono text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
								/>
							</div>
						{/if}

						<!-- Quantity -->
						<div class="w-16 shrink-0">
							<label
								for={`li-qty-${row.key}`}
								class="mb-1 block text-[11px] font-semibold text-slate-600"
							>
								Qty
							</label>
							<input
								id={`li-qty-${row.key}`}
								type="number"
								min="1"
								step="1"
								bind:value={row.quantity}
								class="block w-full rounded-lg border-slate-300 px-2 py-1.5 text-center font-mono text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
						</div>

						<!-- Amount -->
						<div class="w-28 shrink-0">
							<span class="mb-1 block text-right text-[11px] font-semibold text-slate-600"
								>Amount</span
							>
							<div
								class="flex h-[34px] items-center justify-end rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-right font-mono text-xs font-bold text-slate-900"
							>
								{fmtPrice(amount)}
							</div>
						</div>

						<!-- Action: Remove Icon Button -->
						<div class="shrink-0 pb-0.5">
							<button
								type="button"
								onclick={() => removeRow(row.key)}
								aria-label="Remove line item"
								title="Remove item"
								class="inline-flex h-[34px] w-[34px] items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-400 shadow-2xs transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-600 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
							>
								<Icon icon={trashCanOutline} class="h-4 w-4" />
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- ══════════════════════════════════════════════════════════════ -->
	<!-- 5. Totals Section -->
	<!-- ══════════════════════════════════════════════════════════════ -->
	<section
		class="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs"
		aria-labelledby="totals-h"
	>
		<h2 id="totals-h" class="text-sm font-bold text-slate-900">Summary & Totals</h2>
		<dl class="mt-3 max-w-xs space-y-1.5 text-sm">
			<div class="flex justify-between">
				<dt class="text-slate-500">Subtotal</dt>
				<dd class="font-medium text-slate-900">{fmtPrice(subtotal)}</dd>
			</div>
			{#if discount}
				<div class="flex items-center justify-between gap-3">
					<dt class="flex items-center gap-2 text-slate-500">
						Discount
						<span
							class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
						>
							Project discount
						</span>
					</dt>
					<dd class="font-medium text-red-600">−{fmtPrice(discount.amount)}</dd>
				</div>
			{/if}
			<div class="flex justify-between">
				<dt class="text-slate-500">Tax</dt>
				<dd class="font-medium text-slate-900">{fmtPrice(0)}</dd>
			</div>
			<div class="flex justify-between border-t border-slate-200 pt-2">
				<dt class="font-semibold text-slate-900">Total</dt>
				<dd class="font-bold text-indigo-600 text-base">{fmtPrice(total)}</dd>
			</div>
		</dl>
	</section>

	<!-- ══════════════════════════════════════════════════════════════ -->
	<!-- Actions -->
	<!-- ══════════════════════════════════════════════════════════════ -->
	<div class="flex flex-wrap items-center gap-3 pt-2">
		<button
			type="submit"
			disabled={busy}
			aria-busy={busy}
			class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-2xs hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
		>
			{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
			Create invoice
		</button>
		<a
			href={resolve('/app/invoices')}
			class="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-2xs hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition-colors"
		>
			Cancel
		</a>
	</div>
</form>
