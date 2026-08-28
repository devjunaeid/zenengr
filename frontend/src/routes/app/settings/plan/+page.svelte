<script>
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { humanize } from '$lib/utils/format.js';
	import Icon from '@iconify/svelte';
	import chartDonut from '@iconify-icons/mdi/chart-donut';
	import shieldStarOutline from '@iconify-icons/mdi/shield-star-outline';
	import checkCircle from '@iconify-icons/mdi/check-circle';
	import lockOutline from '@iconify-icons/mdi/lock-outline';

	let { data } = $props();

	function getUsagePct(used, limit) {
		if (!limit || limit <= 0) return 0;
		return Math.min(100, Math.round(((used || 0) / limit) * 100));
	}

	function formatQuotaVal(key, val) {
		if (key === 'max_storage_mb') {
			const num = Number(val) || 0;
			if (num >= 1024) return `${(num / 1024).toFixed(1)} GB`;
			return `${num} MB`;
		}
		return `${val}`;
	}

	function formatRemaining(key, used, limit) {
		const diff = Math.max(0, (limit || 0) - (used || 0));
		if (key === 'max_storage_mb') {
			if (diff >= 1024) return `${(diff / 1024).toFixed(1)} GB remaining`;
			return `${diff.toFixed(1)} MB remaining`;
		}
		return `${diff} remaining`;
	}

	function formatResourceTitle(key) {
		if (key === 'max_storage_mb') return 'File Storage';
		if (key === 'max_active_projects') return 'Active Projects';
		if (key === 'max_admin_users') return 'Team Members';
		if (key === 'max_clients') return 'Clients';
		return humanize(key.replace(/^max_/, ''));
	}
</script>

<svelte:head><title>Plan &amp; Usage — ZenEngr</title></svelte:head>

<div class="space-y-6">
	<!-- Current Subscription Plan Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
			<div class="flex items-center gap-3.5">
				<div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
					<Icon icon={shieldStarOutline} class="h-6 w-6" />
				</div>
				<div>
					<div class="flex items-center gap-2.5">
						<h2 class="text-base font-bold text-slate-900">{data.plan.plan_name} Plan</h2>
						{#if data.profile.subscription_status}
							<StatusBadge status={data.profile.subscription_status} />
						{/if}
					</div>
					<p class="text-xs text-slate-500 mt-0.5">Your organization's active tier and allocated resource limits.</p>
				</div>
			</div>

			<div class="flex items-center gap-2">
				<span class="rounded-lg bg-indigo-50/80 px-3 py-1.5 text-xs font-bold text-indigo-700">
					Active Subscription
				</span>
			</div>
		</div>
	</section>

	<!-- Resource Limits & Usage Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
			<div class="flex items-center gap-2.5">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
					<Icon icon={chartDonut} class="h-4 w-4" />
				</div>
				<div>
					<h2 class="text-sm font-bold text-slate-900">Resource Limits &amp; Consumption</h2>
					<p class="text-xs text-slate-500">Live tracker of real-time usage across your tenant.</p>
				</div>
			</div>
		</div>

		<div class="p-6 grid gap-5 sm:grid-cols-2">
			{#each Object.entries(data.plan.limits) as [key, limit] (key)}
				{@const used = data.plan.usage[key.replace(/^max_/, '')] ?? 0}
				{@const pct = getUsagePct(used, limit)}
				<div class="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
					<div class="flex items-center justify-between">
						<span class="text-xs font-bold uppercase tracking-wider text-slate-700">
							{formatResourceTitle(key)}
						</span>
						<span class="text-xs font-semibold text-slate-900">
							<span class="font-bold text-indigo-600">{formatQuotaVal(key, used)}</span> / {formatQuotaVal(key, limit)}
						</span>
					</div>

					<div class="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-slate-200/80">
						<div
							class="h-full rounded-full transition-all duration-500 {pct >= 90
								? 'bg-red-500'
								: pct >= 75
									? 'bg-amber-500'
									: 'bg-indigo-600'}"
							style="width: {pct}%"
						></div>
					</div>

					<div class="mt-2 flex justify-between text-[11px] text-slate-400">
						<span>{pct}% utilized</span>
						<span>{formatRemaining(key, used, limit)}</span>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- Feature Flags Card -->
	<section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
		<div class="border-b border-slate-100 bg-slate-50/60 px-6 py-4">
			<div class="flex items-center gap-2.5">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
					<Icon icon={checkCircle} class="h-4 w-4" />
				</div>
				<div>
					<h2 class="text-sm font-bold text-slate-900">Plan Feature Access</h2>
					<p class="text-xs text-slate-500">Modules and platform capabilities enabled for this tier.</p>
				</div>
			</div>
		</div>

		<div class="p-6">
			{#if data.flags.length === 0}
				<p class="text-xs text-slate-500">No feature flags resolved for this plan.</p>
			{:else}
				<div class="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
					{#each data.flags as flag (flag.key)}
						<div class="flex items-center justify-between rounded-lg border border-slate-100 p-3 {flag.enabled ? 'bg-emerald-50/40 border-emerald-100' : 'bg-slate-50 border-slate-100'}">
							<div class="flex items-center gap-2">
								<Icon
									icon={flag.enabled ? checkCircle : lockOutline}
									class="h-4 w-4 shrink-0 {flag.enabled ? 'text-emerald-600' : 'text-slate-400'}"
								/>
								<span class="text-xs font-semibold text-slate-800 font-mono">{flag.key}</span>
							</div>
							<span class="text-[11px] font-bold {flag.enabled ? 'text-emerald-700' : 'text-slate-400'}">
								{flag.enabled ? 'Enabled' : 'Disabled'}
							</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</section>
</div>
