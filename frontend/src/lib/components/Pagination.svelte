<script>
	import Icon from '@iconify/svelte';
	import chevronLeft from '@iconify-icons/mdi/chevron-left';
	import chevronRight from '@iconify-icons/mdi/chevron-right';

	/**
	 * Prev/next pager with page count.
	 * @type {{ page: number, pageSize: number, total: number, onpage: (page: number) => void }}
	 */
	let { page, pageSize, total, onpage } = $props();

	let pages = $derived(Math.max(1, Math.ceil(total / pageSize)));
	let start = $derived(total === 0 ? 0 : (page - 1) * pageSize + 1);
	let end = $derived(Math.min(total, page * pageSize));
</script>

{#if total > 0}
	<nav
		class="flex items-center justify-between border-t border-slate-200 px-4 py-3"
		aria-label="Pagination"
	>
		<p class="text-sm text-slate-600">
			Showing <span class="font-medium">{start}</span>–<span class="font-medium">{end}</span> of
			<span class="font-medium">{total}</span>
		</p>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
				disabled={page <= 1}
				aria-label="Previous page"
				title="Previous page"
				onclick={() => onpage(page - 1)}
			>
				<Icon icon={chevronLeft} class="h-4 w-4" />
			</button>
			<span class="text-sm text-slate-600">Page {page} of {pages}</span>
			<button
				type="button"
				class="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
				disabled={page >= pages}
				aria-label="Next page"
				onclick={() => onpage(page + 1)}
			>
				<Icon icon={chevronRight} class="h-4 w-4" />
			</button>
		</div>
	</nav>
{/if}
