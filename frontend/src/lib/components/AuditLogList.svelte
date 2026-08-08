<script>
	import Icon from '@iconify/svelte';
	import {
		auditActionLabel,
		auditEntityHref,
		auditGroup,
		formatAuditDetails,
		groupIcon
	} from '$lib/utils/audit.js';
	import { formatDate, formatDateTime, humanize } from '$lib/utils/format.js';

	/**
	 * Shared audit / activity timeline.
	 *
	 * @type {{
	 *   entries: Array<Record<string, any>>,
	 *   linkPrefix?: string|null
	 * }}
	 */
	let { entries = [], linkPrefix = '/app' } = $props();

	/** @param {Record<string, any>} entry */
	function actorName(entry) {
		return entry.actor_name || (entry.actor_type ? humanize(entry.actor_type) : 'System');
	}

	/**
	 * @param {Record<string, any>} entry
	 * @returns {{ label: string, href: string|null }}
	 */
	function entityInfo(entry) {
		const label = entry.entity_label || (entry.entity_type ? humanize(entry.entity_type) : '');
		let href = null;
		if (linkPrefix && entry.entity_label) {
			const route = auditEntityHref(entry.entity_type, entry.entity_id);
			if (route) href = `${linkPrefix}${route}`;
		}
		return { label: label || '—', href };
	}

	/** @param {Record<string, any>} entry */
	function detailRows(entry) {
		return formatAuditDetails(entry.details);
	}

	let today = $derived(formatDate(new Date().toISOString()));
	let yesterday = $derived(formatDate(new Date(Date.now() - 86_400_000).toISOString()));

	/** @param {string} day */
	function dayLabel(day) {
		if (day === today) return 'Today';
		if (day === yesterday) return 'Yesterday';
		return day;
	}

	/**
	 * Entries grouped by calendar day, preserving order.
	 * @type {Array<{ day: string, items: Array<Record<string, any>> }>}
	 */
	let groups = $derived.by(() => {
		/** @type {Array<{ day: string, items: Array<Record<string, any>> }>} */
		const out = [];
		/** @type {{ day: string, items: Array<Record<string, any>> }|null} */
		let current = null;
		for (const entry of entries) {
			const day = formatDate(entry.created_at);
			if (!current || current.day !== day) {
				current = { day, items: [] };
				out.push(current);
			}
			current.items.push(entry);
		}
		return out;
	});
</script>

{#if entries.length === 0}
	<p class="px-6 py-8 text-sm text-slate-500">No activity yet.</p>
{:else}
	<div class="divide-y divide-slate-100">
		{#each groups as group (group.day)}
			<section aria-label={dayLabel(group.day)}>
				<h3
					class="sticky top-0 z-10 border-b border-slate-200 bg-slate-50/95 px-6 py-2 text-xs font-semibold tracking-wide text-slate-500 uppercase backdrop-blur"
				>
					{dayLabel(group.day)}
				</h3>
				<ul class="divide-y divide-slate-100">
					{#each group.items as entry (entry.id)}
						{@const rows = detailRows(entry)}
						{@const entity = entityInfo(entry)}
						<li class="flex gap-3 px-6 py-3 hover:bg-slate-50">
							<span
								class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500"
							>
								<Icon icon={groupIcon(auditGroup(entry.action))} class="h-4 w-4" />
							</span>
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
									<span class="text-sm font-medium text-slate-900">
										{auditActionLabel(entry.action)}
									</span>
									<span class="text-xs text-slate-500">
										{formatDateTime(entry.created_at)}
									</span>
								</div>
								<div
									class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-500"
								>
									<span
										class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-slate-600"
									>
										{actorName(entry)}
									</span>
									<!-- eslint-disable svelte/no-navigation-without-resolve -- dynamic entity route from auditEntityHref + linkPrefix prop -->
									{#if entity.href}
										<a
											href={entity.href}
											class="font-medium text-indigo-600 hover:text-indigo-500 hover:underline"
										>
											{entity.label}
										</a>
									{:else}
										<span>{entity.label}</span>
									{/if}
									<!-- eslint-enable svelte/no-navigation-without-resolve -->
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
				</ul>
			</section>
		{/each}
	</div>
{/if}
