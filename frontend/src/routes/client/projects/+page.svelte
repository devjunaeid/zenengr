<script>
	import EmptyState from '$lib/components/EmptyState.svelte';
</script>

<svelte:head><title>Projects — Client Portal</title></svelte:head>

<h1 class="text-xl font-semibold text-slate-900">Projects</h1>
<p class="mt-1 text-sm text-slate-500">View your active projects and their progress.</p>

<div class="mt-6">
	<EmptyState
		title="No projects yet"
		description="Your projects will appear here once they are created by your service provider."
	/>
</div>
