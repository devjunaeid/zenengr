<script>
	/**
	 * Empty state region with headline + helpful copy + optional CTA slot.
	 * `level` picks the heading tag (clamped to h1–h4) so list pages can
	 * keep a valid heading outline; defaults to h2.
	 * @type {{ title: string, description?: string, level?: number, children?: import('svelte').Snippet }}
	 */
	let { title, description = '', level = 2, children } = $props();
</script>

<section
	class="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center"
	aria-label="No items"
>
	<svelte:element
		this={`h${Math.min(Math.max(level, 1), 4)}`}
		class="text-sm font-semibold text-slate-900"
	>
		{title}
	</svelte:element>
	{#if description}
		<p class="mt-1 text-sm text-slate-500">{description}</p>
	{/if}
	{#if children}
		<div class="mt-4">{@render children()}</div>
	{/if}
</section>
