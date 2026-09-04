<script>
	import Skeleton from './Skeleton.svelte';

	/**
	 * @typedef {Object} Props
	 * @property {number} [count] Number of cards to render (default: 3)
	 * @property {string} [class] Additional container classes
	 */

	let { count = 3, class: className = '' } = $props();
</script>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-{count} {className}">
	<!-- eslint-disable-next-line no-unused-vars -- skeleton placeholder loop; item value unused -->
	{#each Array(count) as _, i (i)}
		<div
			class="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
		>
			<div class="flex items-center justify-between">
				<Skeleton class="h-4 w-28" />
				<Skeleton class="h-8 w-8 rounded-lg" />
			</div>
			<div class="mt-4 space-y-2">
				<Skeleton class="h-8 {i % 2 === 0 ? 'w-32' : 'w-24'}" />
				<div class="flex items-center gap-2">
					<Skeleton class="h-3.5 w-16" />
					<Skeleton class="h-3.5 w-24" />
				</div>
			</div>
		</div>
	{/each}
</div>
