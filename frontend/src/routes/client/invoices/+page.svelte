<script>
	import EmptyState from '$lib/components/EmptyState.svelte';
</script>

<svelte:head><title>Invoices — Client Portal</title></svelte:head>

<h1 class="text-xl font-semibold text-slate-900">Invoices</h1>
<p class="mt-1 text-sm text-slate-500">View and manage your invoices.</p>

<div class="mt-6">
	<EmptyState
		title="No invoices yet"
		description="Invoices will appear here once they are issued for your projects."
	/>
</div>
