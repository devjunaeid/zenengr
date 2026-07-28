<script>
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

	// Layout guard guarantees these exist
	const user = /** @type {import('$lib/api/portal.js').PortalUser} */ (portalAuth.user);
	const client = /** @type {import('$lib/api/portal.js').PortalClient} */ (portalAuth.client);
</script>

<svelte:head><title>Dashboard — Client Portal</title></svelte:head>

<div class="space-y-6">
	<div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
		<h1 class="text-xl font-semibold text-slate-900">
			Welcome, {user.full_name}
		</h1>
		<p class="mt-1 text-sm text-slate-500">
			{client.name}
			<span class="ml-2 inline-block align-middle">
				<StatusBadge status={client.status} />
			</span>
		</p>
	</div>

	<div
		class="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center"
		aria-label="Coming soon"
	>
		<h2 class="text-sm font-semibold text-slate-900">Projects and invoices coming soon</h2>
		<p class="mt-1 text-sm text-slate-500">
			Your projects and invoices will appear here once your service provider sets them up.
		</p>
	</div>
</div>
