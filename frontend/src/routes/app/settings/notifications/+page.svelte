<script>
	import Icon from '@iconify/svelte';
	import emailOutline from '@iconify-icons/mdi/email-outline';
	import bellOutline from '@iconify-icons/mdi/bell-outline';
	import checkCircle from '@iconify-icons/mdi/check-circle';
	import { untrack } from 'svelte';
	import * as accountApi from '$lib/api/account.js';
	import { ApiError } from '$lib/api/client.js';
	import ToggleSwitch from '$lib/components/ToggleSwitch.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { humanize } from '$lib/utils/format.js';

	let { data } = $props();
	const token = auth.token;

	const EVENT_TYPES = [
		'new_comment',
		'invoice_issued',
		'payment_received',
		'refund_recorded',
		'advance_applied',
		'milestone_completed',
		'project_created'
	];

	const EVENT_METADATA = {
		new_comment: {
			label: 'New Discussion Comment',
			description: 'When a team member or client posts a comment on a project.'
		},
		invoice_issued: {
			label: 'Invoice Issued',
			description: 'When a new draft invoice is officially issued to a client.'
		},
		payment_received: {
			label: 'Payment Received',
			description: 'When a transaction payment is successfully recorded on an invoice.'
		},
		refund_recorded: {
			label: 'Refund Recorded',
			description: 'When a credit or payment refund is processed on a ledger.'
		},
		advance_applied: {
			label: 'Advance Credit Applied',
			description: 'When available client credit is used toward an invoice balance.'
		},
		milestone_completed: {
			label: 'Milestone Completed',
			description: 'When a service milestone step is marked as done.'
		},
		project_created: {
			label: 'Project Created',
			description: 'When a new client project workspace is initialized.'
		}
	};

	function buildPrefs(loaded) {
		return EVENT_TYPES.map((eventType) => {
			const found = loaded.find((p) => p.event_type === eventType);
			return { event_type: eventType, enabled: found ? found.enabled : false };
		});
	}

	let emailPrefs = $state(buildPrefs(untrack(() => data.prefs)));
	let inappPrefs = $state(buildPrefs(untrack(() => data.inappPrefs)));
	let savingPref = $state(null);
	let prefsError = $state(null);
	let prefsSaved = $state(false);

	const emailOnCount = $derived(emailPrefs.filter((p) => p.enabled).length);
	const inappOnCount = $derived(inappPrefs.filter((p) => p.enabled).length);

	async function togglePref(channel, eventType, enabled) {
		if (savingPref) return;
		savingPref = `${channel}:${eventType}`;
		prefsError = null;
		prefsSaved = false;
		const arr = channel === 'inapp' ? inappPrefs : emailPrefs;
		const idx = arr.findIndex((x) => x.event_type === eventType);
		if (idx < 0) return;
		const previous = arr[idx].enabled;
		arr[idx].enabled = enabled;
		try {
			const updated = await accountApi.updateNotificationPreferences(
				fetch,
				token,
				{ channel, preferences: [{ event_type: eventType, enabled }] },
				{ realm: 'admin' }
			);
			for (const p of updated) {
				const i = arr.findIndex((x) => x.event_type === p.event_type);
				if (i >= 0) arr[i].enabled = p.enabled;
			}
			prefsSaved = true;
			setTimeout(() => (prefsSaved = false), 2000);
		} catch (e) {
			arr[idx].enabled = previous;
			prefsError = e instanceof ApiError ? e.message : 'Unable to save preference. Try again.';
		} finally {
			savingPref = null;
		}
	}

	function toggleKey(channel, pref) {
		return `${channel}:${pref.event_type}`;
	}
</script>

<svelte:head><title>Notifications — ZenEngr</title></svelte:head>

<div class="space-y-6">
	{#if prefsError}
		<div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-800 shadow-2xs">
			{prefsError}
		</div>
	{/if}
	{#if prefsSaved}
		<div role="status" class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-800 shadow-2xs flex items-center gap-1.5 animate-fade-in">
			<Icon icon={checkCircle} class="h-4 w-4 text-emerald-600" />
			Notification preferences saved.
		</div>
	{/if}

	<!-- In-App Notifications Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
			<div class="flex items-center gap-2.5">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
					<Icon icon={bellOutline} class="h-4 w-4" />
				</div>
				<div>
					<h2 class="text-sm font-bold text-slate-900">In-App Notification Feed</h2>
					<p class="text-xs text-slate-500">Real-time alerts shown in your top bell activity center.</p>
				</div>
			</div>
			<span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
				{inappOnCount} of {EVENT_TYPES.length} active
			</span>
		</div>

		<div class="divide-y divide-slate-100">
			{#each inappPrefs as pref (pref.event_type)}
				{@const meta = EVENT_METADATA[pref.event_type] || { label: humanize(pref.event_type), description: '' }}
				<div class="flex items-center justify-between p-5 hover:bg-slate-50/40 transition-colors">
					<div class="max-w-lg">
						<p class="text-sm font-semibold text-slate-900">{meta.label}</p>
						<p class="mt-0.5 text-xs text-slate-500">{meta.description}</p>
					</div>
					<ToggleSwitch
						checked={pref.enabled}
						disabled={savingPref === toggleKey('inapp', pref)}
						label={`In-app: ${meta.label}`}
						onchange={(enabled) => togglePref('inapp', pref.event_type, enabled)}
					/>
				</div>
			{/each}
		</div>
	</section>

	<!-- Email Notifications Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
			<div class="flex items-center gap-2.5">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
					<Icon icon={emailOutline} class="h-4 w-4" />
				</div>
				<div>
					<h2 class="text-sm font-bold text-slate-900">Email Notifications</h2>
					<p class="text-xs text-slate-500">Direct transactional email summaries delivered to your inbox.</p>
				</div>
			</div>
			<span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
				{emailOnCount} of {EVENT_TYPES.length} active
			</span>
		</div>

		<div class="divide-y divide-slate-100">
			{#each emailPrefs as pref (pref.event_type)}
				{@const meta = EVENT_METADATA[pref.event_type] || { label: humanize(pref.event_type), description: '' }}
				<div class="flex items-center justify-between p-5 hover:bg-slate-50/40 transition-colors">
					<div class="max-w-lg">
						<p class="text-sm font-semibold text-slate-900">{meta.label}</p>
						<p class="mt-0.5 text-xs text-slate-500">{meta.description}</p>
					</div>
					<ToggleSwitch
						checked={pref.enabled}
						disabled={savingPref === toggleKey('email', pref)}
						label={`Email: ${meta.label}`}
						onchange={(enabled) => togglePref('email', pref.event_type, enabled)}
					/>
				</div>
			{/each}
		</div>
	</section>
</div>
