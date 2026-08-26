<script>
	import { navigating } from '$app/state';
	import { onMount } from 'svelte';

	let progress = $state(0);
	let isVisible = $state(false);
	let timer = null;

	$effect(() => {
		if (navigating.to) {
			isVisible = true;
			progress = 15;

			if (timer) clearInterval(timer);
			timer = setInterval(() => {
				if (progress < 85) {
					// Exponential slowdown as it approaches 85%
					const diff = (85 - progress) * 0.15;
					progress += Math.max(diff, 1.5);
				}
			}, 100);
		} else {
			if (timer) clearInterval(timer);
			if (isVisible) {
				progress = 100;
				const timeout = setTimeout(() => {
					isVisible = false;
					progress = 0;
				}, 250);
				return () => clearTimeout(timeout);
			}
		}
	});
</script>

{#if isVisible}
	<div
		class="fixed inset-x-0 top-0 z-50 h-1 overflow-hidden bg-transparent"
		role="progressbar"
		aria-valuemin="0"
		aria-valuemax="100"
		aria-valuenow={Math.round(progress)}
	>
		<div
			class="h-full bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-500 shadow-sm transition-all duration-200 ease-out"
			style="width: {progress}%; box-shadow: 0 0 10px rgba(99, 102, 241, 0.6);"
		></div>
	</div>
{/if}
