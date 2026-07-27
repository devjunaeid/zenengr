<script>
	import { resolve } from '$app/paths';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { humanize } from '$lib/utils/format.js';

	let { data } = $props();
</script>

<svelte:head><title>Plan &amp; usage — ZenEngr</title></svelte:head>

<nav class="text-sm text-slate-500" aria-label="Breadcrumb">
	<a href={resolve('/app/settings')} class="text-indigo-600 hover:text-indigo-500">Settings</a>
	<span aria-hidden="true"> / </span>
	<span>Plan &amp; usage</span>
</nav>

<div class="mt-2 flex flex-wrap items-center gap-3">
	<h1 class="text-2xl font-semibold text-slate-900">Plan &amp; usage</h1>
	{#if data.profile.subscription_status}
		<StatusBadge status={data.profile.subscription_status} />
	{/if}
</div>
<p class="mt-1 text-sm text-slate-500">
	Current plan: <span class="font-medium text-slate-700">{data.plan.plan_name}</span>
</p>

<section
	class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
	aria-labelledby="usage-h"
>
	<h2
		id="usage-h"
		class="border-b border-slate-200 px-6 py-4 text-base font-semibold text-slate-900"
	>
		Limits &amp; usage
	</h2>
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-200">
			<thead class="bg-slate-50">
				<tr>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Resource</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Used</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Limit</th
					>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-200">
				{#each Object.entries(data.plan.limits) as [key, limit] (key)}
					<tr>
						<td class="px-4 py-3 text-sm text-slate-800">{humanize(key)}</td>
						<td class="px-4 py-3 text-right text-sm text-slate-600">
							{data.plan.usage[key.replace(/^max_/, '')] ?? 0}
						</td>
						<td class="px-4 py-3 text-right text-sm text-slate-600">{limit}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>

<section
	class="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
	aria-labelledby="flags-h"
>
	<h2 id="flags-h" class="text-base font-semibold text-slate-900">Feature flags</h2>
	{#if data.flags.length === 0}
		<p class="mt-2 text-sm text-slate-500">No feature flags resolved for this plan.</p>
	{:else}
		<ul class="mt-3 flex flex-wrap gap-2">
			{#each data.flags as flag (flag.key)}
				<li
					class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset {flag.enabled
						? 'bg-green-100 text-green-800 ring-green-600/20'
						: 'bg-slate-100 text-slate-600 ring-slate-500/20'}"
				>
					<span class="font-mono">{flag.key}</span>
					<span>{flag.enabled ? 'On' : 'Off'}</span>
				</li>
			{/each}
		</ul>
	{/if}
</section>
