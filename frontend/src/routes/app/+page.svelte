<script>
	import { auth } from '$lib/stores/auth.svelte.js';
	import { humanize } from '$lib/utils/format.js';

	let { data } = $props();
</script>

<svelte:head><title>Dashboard — ZenEngr</title></svelte:head>

<h1 class="text-2xl font-semibold text-slate-900">Dashboard</h1>
<p class="mt-1 text-sm text-slate-500">
	Welcome back, {auth.user?.full_name}. Plan: <span class="font-medium">{data.plan.plan_name}</span>
</p>

<div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
	{#each Object.entries(data.plan.limits) as [key, limit] (key)}
		{@const used = data.plan.usage[key.replace(/^max_/, '')] ?? 0}
		<div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
			<p class="text-xs font-medium tracking-wide text-slate-500 uppercase">{humanize(key)}</p>
			<p class="mt-2 text-2xl font-semibold text-slate-900">
				{used}<span class="text-base font-normal text-slate-400"> / {limit}</span>
			</p>
			<div
				class="mt-3 h-1.5 w-full rounded-full bg-slate-100"
				role="progressbar"
				aria-valuenow={used}
				aria-valuemin={0}
				aria-valuemax={limit}
				aria-label={`${humanize(key)} usage`}
			>
				<div
					class="h-1.5 rounded-full bg-indigo-600"
					style="width: {Math.min(100, limit > 0 ? (used / limit) * 100 : 0)}%"
				></div>
			</div>
		</div>
	{/each}
</div>

<section
	class="mt-6 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center"
	aria-label="Coming soon"
>
	<h2 class="text-sm font-semibold text-slate-900">Workspace modules coming soon</h2>
	<p class="mt-1 text-sm text-slate-500">
		Clients, projects, invoices and comments will appear here in the next delivery batch.
	</p>
</section>
