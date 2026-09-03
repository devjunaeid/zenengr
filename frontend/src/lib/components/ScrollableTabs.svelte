<script>
	import Icon from '@iconify/svelte';
	import chevronLeft from '@iconify-icons/mdi/chevron-left';
	import chevronRight from '@iconify-icons/mdi/chevron-right';

	/**
	 * @type {{
	 *   ariaLabel?: string,
	 *   class?: string,
	 *   children?: import('svelte').Snippet
	 * }}
	 */
	let { ariaLabel = 'Navigation tabs', class: className = '', children } = $props();

	let container = $state(/** @type {HTMLElement|null} */ (null));
	let canScrollLeft = $state(false);
	let canScrollRight = $state(false);

	function updateScroll() {
		if (!container) return;
		canScrollLeft = container.scrollLeft > 6;
		canScrollRight = container.scrollLeft < container.scrollWidth - container.clientWidth - 6;
	}

	$effect(() => {
		if (!container) return;
		updateScroll();
		const ro = new ResizeObserver(updateScroll);
		ro.observe(container);
		container.addEventListener('scroll', updateScroll, { passive: true });
		return () => {
			ro.disconnect();
			container?.removeEventListener('scroll', updateScroll);
		};
	});

	function scrollLeft() {
		container?.scrollBy({ left: -220, behavior: 'smooth' });
	}

	function scrollRight() {
		container?.scrollBy({ left: 220, behavior: 'smooth' });
	}
</script>

<div class="relative group/tabs {className}">
	<!-- Left scroll indicator & button -->
	{#if canScrollLeft}
		<div
			class="pointer-events-none absolute inset-y-0 left-0 z-10 flex w-12 items-center justify-start rounded-l-xl bg-gradient-to-r from-white via-white/90 to-transparent pl-1"
		>
			<button
				type="button"
				onclick={scrollLeft}
				class="pointer-events-auto flex h-7 w-7 items-center justify-center rounded-full bg-white text-slate-600 shadow-md ring-1 ring-slate-200 transition-transform hover:scale-105 hover:text-indigo-600 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
				aria-label="Scroll tabs left"
			>
				<Icon icon={chevronLeft} class="h-4 w-4" />
			</button>
		</div>
	{/if}

	<!-- Scrollable track -->
	<nav
		bind:this={container}
		aria-label={ariaLabel}
		class="flex items-center gap-1.5 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-2xs scroll-smooth [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
	>
		{@render children?.()}
	</nav>

	<!-- Right scroll indicator & button -->
	{#if canScrollRight}
		<div
			class="pointer-events-none absolute inset-y-0 right-0 z-10 flex w-12 items-center justify-end rounded-r-xl bg-gradient-to-l from-white via-white/90 to-transparent pr-1"
		>
			<button
				type="button"
				onclick={scrollRight}
				class="pointer-events-auto flex h-7 w-7 items-center justify-center rounded-full bg-white text-slate-600 shadow-md ring-1 ring-slate-200 transition-transform hover:scale-105 hover:text-indigo-600 focus:ring-2 focus:ring-indigo-500 focus:outline-none animate-pulse sm:animate-none"
				aria-label="Scroll tabs right"
			>
				<Icon icon={chevronRight} class="h-4 w-4" />
			</button>
		</div>
	{/if}
</div>
