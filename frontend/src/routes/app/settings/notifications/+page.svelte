<script>
	import Icon from '@iconify/svelte';
	import chevronDown from '@iconify-icons/mdi/chevron-down';
	import { untrack } from 'svelte';
	import * as accountApi from '$lib/api/account.js';
	import { ApiError } from '$lib/api/client.js';
	import ToggleSwitch from '$lib/components/ToggleSwitch.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { humanize } from '$lib/utils/format.js';

	let { data } = $props();
	const token = /** @type {string} */ (auth.token);

	const EVENT_TYPES = [
		'new_comment',
		'invoice_issued',
		'payment_received',
		'refund_recorded',
		'advance_applied',
		'milestone_completed',
		'project_created'
	];

	/** @type {Record<string, string>} */
	const EVENT_LABELS = {
		new_comment: 'New comment',
		invoice_issued: 'Invoice issued',
		payment_received: 'Payment received',
		refund_recorded: 'Refund recorded',
		advance_applied: 'Advance applied',
		milestone_completed: 'Milestone completed',
		project_created: 'Project created'
	};

	/**
	 * Normalize the backend list into the canonical 7-entry order so every
	 * toggle row renders even when an event has no stored preference yet.
	 * @param {Array<{ event_type: string, enabled: boolean }>} loaded
	 */
	function buildPrefs(loaded) {
		return EVENT_TYPES.map((eventType) => {
			const found = loaded.find((p) => p.event_type === eventType);
			return { event_type: eventType, enabled: found ? found.enabled : false };
		});
	}

	let emailPrefs = $state(buildPrefs(untrack(() => data.prefs)));
	let inappPrefs = $state(buildPrefs(untrack(() => data.inappPrefs)));
	/** @type {string|null} */
	let savingPref = $state(null);
	/** @type {string|null} */
	let prefsError = $state(null);
	let prefsSaved = $state(false);

	const emailOnCount = $derived(emailPrefs.filter((p) => p.enabled).length);
	const inappOnCount = $derived(inappPrefs.filter((p) => p.enabled).length);

	/**
	 * Flip a single preference and PATCH it immediately. Optimistic: the row
	 * updates right away and reverts if the backend rejects the change.
	 * @param {'email'|'inapp'} channel
	 * @param {string} eventType
	 * @param {boolean} enabled
	 */
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

	/**
	 * @param {string} channel
	 * @param {{ event_type: string, enabled: boolean }} pref
	 */
	function toggleKey(channel, pref) {
		return `${channel}:${pref.event_type}`;
	}
</script>

<svelte:head><title>Notifications — ZenEngr</title></svelte:head>

<h1 class="text-2xl font-semibold text-slate-900">Notifications</h1>
<p class="mt-1 text-sm text-slate-500">
	Control which events notify you — Email vs in-app independently.
</p>

<div class="mt-6 space-y-6">
	{#if prefsError}
		<div
			role="alert"
			class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{prefsError}
		</div>
	{:else if prefsSaved}
		<div
			role="status"
			class="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
		>
			Saved
		</div>
	{/if}

	<!-- Email -->
	<details open class="group rounded-lg border border-slate-200 bg-white shadow-sm">
		<summary
			class="flex cursor-pointer list-none items-center justify-between gap-2 rounded-lg px-6 py-4 select-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none [&::-webkit-details-marker]:hidden"
		>
			<span class="flex flex-wrap items-center gap-2">
				<span class="text-base font-semibold text-slate-900">Email notifications</span>
				<span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
					>{emailOnCount} of {EVENT_TYPES.length} on</span
				>
			</span>
			<Icon
				icon={chevronDown}
				class="h-5 w-5 shrink-0 text-slate-400 transition-transform group-open:rotate-180"
			/>
		</summary>
		<div class="border-t border-slate-200 px-6 pb-2">
			<ul class="divide-y divide-slate-200">
				{#each emailPrefs as pref (pref.event_type)}
					<li
						class="flex items-center justify-between py-3"
						aria-busy={savingPref === toggleKey('email', pref)}
					>
						<div>
							<p class="text-sm font-medium text-slate-800">
								{EVENT_LABELS[pref.event_type] ?? humanize(pref.event_type)}
							</p>
							<p class="text-xs text-slate-500">{pref.event_type}</p>
						</div>
						<ToggleSwitch
							checked={pref.enabled}
							disabled={savingPref === toggleKey('email', pref)}
							label={`Email: ${EVENT_LABELS[pref.event_type] ?? humanize(pref.event_type)}`}
							onchange={(enabled) => togglePref('email', pref.event_type, enabled)}
						/>
					</li>
				{/each}
			</ul>
		</div>
	</details>

	<!-- In-app -->
	<details class="group rounded-lg border border-slate-200 bg-white shadow-sm">
		<summary
			class="flex cursor-pointer list-none items-center justify-between gap-2 rounded-lg px-6 py-4 select-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none [&::-webkit-details-marker]:hidden"
		>
			<span class="flex flex-wrap items-center gap-2">
				<span class="text-base font-semibold text-slate-900">In-app notifications</span>
				<span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600"
					>{inappOnCount} of {EVENT_TYPES.length} on</span
				>
			</span>
			<Icon
				icon={chevronDown}
				class="h-5 w-5 shrink-0 text-slate-400 transition-transform group-open:rotate-180"
			/>
		</summary>
		<div class="border-t border-slate-200 px-6 pb-2">
			<ul class="divide-y divide-slate-200">
				{#each inappPrefs as pref (pref.event_type)}
					<li
						class="flex items-center justify-between py-3"
						aria-busy={savingPref === toggleKey('inapp', pref)}
					>
						<div>
							<p class="text-sm font-medium text-slate-800">
								{EVENT_LABELS[pref.event_type] ?? humanize(pref.event_type)}
							</p>
							<p class="text-xs text-slate-500">{pref.event_type}</p>
						</div>
						<ToggleSwitch
							checked={pref.enabled}
							disabled={savingPref === toggleKey('inapp', pref)}
							label={`In-app: ${EVENT_LABELS[pref.event_type] ?? humanize(pref.event_type)}`}
							onchange={(enabled) => togglePref('inapp', pref.event_type, enabled)}
						/>
					</li>
				{/each}
			</ul>
		</div>
	</details>
</div>
