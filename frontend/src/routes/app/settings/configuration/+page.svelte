<script>
	import { untrack } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { ApiError } from '$lib/api/client.js';
	import * as tenantApi from '$lib/api/tenant.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import TimezoneSelect from '$lib/components/TimezoneSelect.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { setTenantSettings } from '$lib/stores/settings.svelte.js';
	import { DATE_FORMATS, formatDate } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import receiptText from '@iconify-icons/mdi/receipt-text';
	import earth from '@iconify-icons/mdi/earth';
	import currencyUsd from '@iconify-icons/mdi/currency-usd';
	import lockOutline from '@iconify-icons/mdi/lock-outline';

	let { data } = $props();

	const DEMO_ISO = '2026-03-05T14:30:00.000Z';

	const token = auth.token;
	let isAdmin = $derived(auth.can('manage', 'tenant_settings'));

	function normalizeVal(key, val) {
		if (key === 'invoice_number_format' && typeof val === 'string' && val.startsWith('INV-')) {
			return '{PREFIX}-' + val.slice(4);
		}
		return val ?? '';
	}

	// Filter out email_sender_identity completely per user request
	let cleanSettings = $derived(data.settings.filter((s) => s.key !== 'email_sender_identity'));

	let drafts = $state(
		untrack(() =>
			Object.fromEntries(data.settings.map((s) => [s.key, normalizeVal(s.key, s.value)]))
		)
	);

	$effect(() => {
		for (const s of data.settings) {
			if (savingKey === null && !savedKeys[s.key]) {
				drafts[s.key] = normalizeVal(s.key, s.value);
			}
		}
	});

	let savingKey = $state(null);
	let savedKeys = $state({});
	let settingsErr = $state(null);

	const INVOICE_NUMBER_FORMAT_OPTIONS = [
		{
			value: '{PREFIX}-{SEQ+1000}',
			render: (p) => `${p}-1001`,
			note: 'Easy to say out loud ("ten-oh-one") · Never overflows'
		},
		{
			value: '{PREFIX}-{YY}-{SEQ+100}',
			render: (p) => `${p}-26-101`,
			note: '2-digit year + series ("twenty-six, one-oh-one")'
		},
		{
			value: '{PREFIX}-{YYYY}-{SEQ+100}',
			render: (p) => `${p}-2026-101`,
			note: 'Full year + series ("twenty-twenty-six, one-oh-one")'
		},
		{
			value: '{PREFIX}-{YYYY}-{SEQ}',
			render: (p) => `${p}-2026-1`,
			note: 'Full year + natural count (e.g. 1, 45, 12000)'
		},
		{
			value: '{PREFIX}-{YY}-{SEQ}',
			render: (p) => `${p}-26-1`,
			note: 'Short year + natural count'
		},
		{
			value: '{PREFIX}-{SEQ}',
			render: (p) => `${p}-1`,
			note: 'Minimal direct sequence (e.g. 1, 42, 1050)'
		},
		{
			value: '{PREFIX}-{YYYY}-{SEQ:04d}',
			render: (p) => `${p}-2026-0001`,
			note: 'Standard 4-digit padded'
		},
		{
			value: '{PREFIX}-{SEQ:04d}',
			render: (p) => `${p}-0001`,
			note: 'Simple 4-digit padded'
		}
	];

	let currentPrefix = $derived((drafts['invoice_prefix'] || 'INV').trim().toUpperCase());

	const SECTIONS = [
		{
			id: 'invoices',
			title: 'Invoice Numbering & Prefix',
			description:
				'Customize sequential numbering conventions and company prefix for generated client invoices.',
			icon: receiptText,
			keys: ['invoice_prefix', 'invoice_number_format']
		},
		{
			id: 'regional',
			title: 'Regional & Date / Time Formats',
			description:
				'Configure standard timezone, date displays, and clock formats across all projects and portals.',
			icon: earth,
			keys: ['timezone', 'date_format', 'time_format']
		},
		{
			id: 'financial',
			title: 'Currency & Accounting',
			description:
				'Default 3-letter currency code applied to pricing, statements, and financial ledgers.',
			icon: currencyUsd,
			keys: ['currency']
		},
		{
			id: 'security',
			title: 'Security & Access Policy',
			description: 'Enforce tenant-wide password complexity requirements for team members.',
			icon: lockOutline,
			keys: ['password_min_length']
		}
	];

	const SETTING_LABELS = {
		invoice_prefix: {
			label: 'Invoice Prefix / Initial',
			description:
				'Custom prefix or company initial used on all generated invoices (e.g. INV, ZEN, BILL).'
		},
		invoice_number_format: {
			label: 'Invoice Number Format',
			description:
				'Sequential numbering pattern with automatic year, prefix, and series formatting.'
		},
		timezone: {
			label: 'Timezone',
			description:
				'Primary IANA timezone used for timestamps, milestone deadlines, and activity logs.'
		},
		date_format: {
			label: 'Date Format',
			description: 'Visual date template applied to project dates, invoices, and exported reports.'
		},
		time_format: {
			label: 'Time Format',
			description: 'Standard 24-hour or 12-hour AM/PM clock display.'
		},
		currency: {
			label: 'Default Currency',
			description: 'ISO 4217 3-letter currency code (e.g. USD, EUR, GBP, CAD, AUD).'
		},
		password_min_length: {
			label: 'Minimum Password Length',
			description: 'Minimum number of characters required for user account passwords.'
		}
	};

	async function saveSetting(key) {
		settingsErr = null;
		savingKey = key;
		let valToSave = drafts[key];
		if (key === 'invoice_prefix') {
			valToSave = (valToSave || 'INV').trim().toUpperCase();
			drafts[key] = valToSave;
		}
		try {
			await tenantApi.updateSetting(fetch, token, key, valToSave);
			setTenantSettings({ [key]: valToSave });
			savedKeys = { ...savedKeys, [key]: 'Saved' };
			setTimeout(() => {
				const next = { ...savedKeys };
				delete next[key];
				savedKeys = next;
			}, 2500);
			await invalidateAll();
		} catch (e) {
			settingsErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			savingKey = null;
		}
	}
</script>

<svelte:head><title>Configuration — ZenEngr</title></svelte:head>

<div class="space-y-6">
	{#if settingsErr}
		<div
			role="alert"
			class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 shadow-2xs"
		>
			<span class="font-semibold">Error:</span>
			{settingsErr}
		</div>
	{/if}

	{#each SECTIONS as section (section.id)}
		{@const sectionSettings = cleanSettings.filter((s) => section.keys.includes(s.key))}
		{#if sectionSettings.length > 0}
			<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
				<!-- Section Header -->
				<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
					<div class="flex items-center gap-2.5">
						<div
							class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
						>
							<Icon icon={section.icon} class="h-4 w-4" />
						</div>
						<div>
							<h2 class="text-sm font-bold text-slate-900">{section.title}</h2>
							<p class="text-xs text-slate-500">{section.description}</p>
						</div>
					</div>
				</div>

				<!-- Section Settings List -->
				<div class="divide-y divide-slate-100">
					{#each sectionSettings as s (s.key)}
						{@const meta = SETTING_LABELS[s.key] || { label: s.key, description: '' }}
						<div
							class="flex flex-col gap-4 p-6 transition-colors hover:bg-slate-50/30 sm:flex-row sm:items-center sm:justify-between"
						>
							<!-- Label & Info -->
							<div class="max-w-md">
								<div class="flex items-center gap-2">
									<label for="set-{s.key}" class="text-sm font-semibold text-slate-900">
										{meta.label}
									</label>
									<code
										class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-400"
									>
										{s.key}
									</code>
								</div>
								{#if meta.description}
									<p class="mt-1 text-xs leading-relaxed text-slate-500">
										{meta.description}
									</p>
								{/if}
							</div>

							<!-- Input & Save Action -->
							<div class="flex flex-wrap items-center gap-3">
								{#if s.editable && isAdmin}
									{#if s.key === 'date_format'}
										<select
											id="set-{s.key}"
											bind:value={drafts[s.key]}
											class="block w-full rounded-lg border-slate-300 py-2 text-xs font-medium text-slate-800 shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 sm:w-64"
										>
											{#each DATE_FORMATS as fmt (fmt)}
												<option value={fmt}>
													{fmt} — {formatDate(DEMO_ISO, { date_format: fmt })}
												</option>
											{/each}
										</select>
									{:else if s.key === 'time_format'}
										<select
											id="set-{s.key}"
											bind:value={drafts[s.key]}
											class="block w-full rounded-lg border-slate-300 py-2 text-xs font-medium text-slate-800 shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 sm:w-56"
										>
											<option value="24h">24h — 14:30 (24-hour)</option>
											<option value="12h">12h — 2:30 PM (12-hour)</option>
										</select>
									{:else if s.key === 'invoice_number_format'}
										<select
											id="set-{s.key}"
											bind:value={drafts[s.key]}
											class="block w-full rounded-lg border-slate-300 py-2 text-xs font-medium text-slate-800 shadow-2xs focus:border-indigo-500 focus:ring-indigo-500 sm:w-72"
										>
											{#if !INVOICE_NUMBER_FORMAT_OPTIONS.some((o) => o.value === drafts[s.key]) && drafts[s.key]}
												<option value={drafts[s.key]}>
													{drafts[s.key]} (Current)
												</option>
											{/if}
											{#each INVOICE_NUMBER_FORMAT_OPTIONS as opt (opt.value)}
												<option value={opt.value}>
													{opt.render(currentPrefix)} — {opt.note}
												</option>
											{/each}
										</select>
									{:else if s.key === 'invoice_prefix'}
										<div class="flex items-center gap-2">
											<input
												id="set-{s.key}"
												type="text"
												maxlength="10"
												bind:value={drafts[s.key]}
												placeholder="INV"
												class="block w-28 rounded-lg border-slate-300 py-2 font-mono text-xs font-bold uppercase shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
											/>
										</div>
									{:else if s.key === 'timezone'}
										<div class="w-full sm:w-64">
											<TimezoneSelect id="set-{s.key}" bind:value={drafts[s.key]} />
										</div>
									{:else if s.key === 'currency'}
										<input
											id="set-{s.key}"
											type="text"
											maxlength="3"
											bind:value={drafts[s.key]}
											placeholder="USD"
											class="block w-28 rounded-lg border-slate-300 py-2 font-mono text-xs font-bold uppercase shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
										/>
									{:else}
										<input
											id="set-{s.key}"
											type="text"
											bind:value={drafts[s.key]}
											placeholder={s.value === null ? '••••••' : ''}
											class="block w-36 rounded-lg border-slate-300 py-2 text-xs shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
										/>
									{/if}

									<!-- Save Button -->
									<div class="flex items-center gap-2">
										{#if savedKeys[s.key]}
											<span
												role="status"
												class="animate-fade-in inline-flex items-center rounded-md bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-600"
											>
												✓ {savedKeys[s.key]}
											</span>
										{/if}
										<button
											type="button"
											disabled={savingKey === s.key}
											aria-busy={savingKey === s.key}
											onclick={() => saveSetting(s.key)}
											class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
										>
											{#if savingKey === s.key}<Spinner class="h-3 w-3 text-white" />{/if}
											Save
										</button>
									</div>
								{:else}
									<span
										class="inline-flex rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700"
									>
										{s.value ?? '••••••'}
									</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}
	{/each}
</div>
