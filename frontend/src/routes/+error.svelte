<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>{page.status} — ZenEngr</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
	<div class="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xs">
		<span
			class="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full font-mono text-lg font-bold {page.status === 404
				? 'bg-amber-100 text-amber-700'
				: 'bg-rose-100 text-rose-700'}"
		>
			{page.status}
		</span>
		<h1 class="mb-2 text-xl font-bold text-slate-900">
			{page.status === 404 ? 'Page Not Found' : 'Something went wrong'}
		</h1>
		<p class="mb-6 text-sm text-slate-600">
			{page.error?.message || 'An unexpected error occurred while loading this page.'}
		</p>
		<div class="flex items-center justify-center gap-3">
			<button
				type="button"
				onclick={() => window.location.reload()}
				class="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-2xs transition-colors hover:bg-indigo-700 focus-visible:outline-none"
			>
				Try Again
			</button>
			<a
				href={resolve('/app')}
				class="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 focus-visible:outline-none"
			>
				Back to Dashboard
			</a>
		</div>
	</div>
</div>
