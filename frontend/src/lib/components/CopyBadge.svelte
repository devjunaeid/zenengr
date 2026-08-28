<script>
	import Icon from '@iconify/svelte';
	import contentCopy from '@iconify-icons/mdi/content-copy';
	import check from '@iconify-icons/mdi/check';
	import { formatProjectCode } from '$lib/utils/format.js';

	let { value, label = null, class: extraClass = '' } = $props();

	let copied = $state(false);
	let timeoutId = null;

	async function copy() {
		if (!value) return;
		try {
			await navigator.clipboard.writeText(String(value));
			copied = true;
			if (timeoutId) clearTimeout(timeoutId);
			timeoutId = setTimeout(() => {
				copied = false;
			}, 2000);
		} catch {
			// fallback if navigator.clipboard is unavailable
			const el = document.createElement('textarea');
			el.value = String(value);
			document.body.appendChild(el);
			el.select();
			document.execCommand('copy');
			document.body.removeChild(el);
			copied = true;
			if (timeoutId) clearTimeout(timeoutId);
			timeoutId = setTimeout(() => {
				copied = false;
			}, 2000);
		}
	}
</script>

<button
	type="button"
	onclick={copy}
	title={`Click to copy Project ID: ${value}`}
	aria-label={`Copy Project ID ${value}`}
	class="group inline-flex items-center gap-1.5 font-mono text-xs font-semibold px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 cursor-pointer shadow-2xs {extraClass}"
>
	<span>{label ?? (value ? formatProjectCode(value) : '—')}</span>
	{#if copied}
		<span class="inline-flex items-center gap-0.5 text-[10px] font-sans font-medium text-emerald-600">
			<Icon icon={check} class="h-3.5 w-3.5 text-emerald-600" />
			Copied
		</span>
	{:else}
		<Icon icon={contentCopy} class="h-3 w-3 text-slate-400 group-hover:text-indigo-600 transition-colors" />
	{/if}
</button>
