<script>
	import { numberToWords } from '$lib/utils/numberToWords.js';

	let { value = '', class: className = '', prefix = '(', suffix = ')' } = $props();

	let words = $derived(numberToWords(value));
</script>

{#if words}
	<span
		class="block text-[11px] font-medium text-indigo-600 dark:text-indigo-400 transition-all {className}"
	>
		{prefix}{words}{suffix}
	</span>
{/if}
