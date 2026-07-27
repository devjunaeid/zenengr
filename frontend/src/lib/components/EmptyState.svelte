<script>
	/**
	 * Empty state region with headline + helpful copy + optional CTA slot.
	 * @type {{ title: string, description?: string, children?: import('svelte').Snippet }}
	 */
	let { title, description = '', children } = $props();
</script>

<section
	class="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center"
	aria-label="No items"
>
	<h3 class="text-sm font-semibold text-slate-900">{title}</h3>
	{#if description}
		<p class="mt-1 text-sm text-slate-500">{description}</p>
	{/if}
	{#if children}
		<div class="mt-4">{@render children()}</div>
	{/if}
</section>
