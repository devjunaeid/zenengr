<script>
	import { resolve } from '$app/paths';
</script>

<svelte:head><title>Client portal — ZenEngr</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
	<div
		class="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm"
	>
		<h1 class="text-xl font-semibold text-slate-900">Client portal</h1>
		<p class="mt-2 text-sm text-slate-500">
			Client portal coming soon. Your service provider will share access details when the portal
			launches.
		</p>
		<p class="mt-6 text-sm">
			<a href={resolve('/login')} class="font-medium text-indigo-600 hover:text-indigo-500">
				Staff sign in
			</a>
		</p>
	</div>
</div>
