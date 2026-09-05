<script>
	import { navigating } from '$app/state';

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
			return () => {
				if (timer) clearInterval(timer);
			};
		} else {
			if (timer) clearInterval(timer);
			if (isVisible) {
				progress = 100;
				const timeout = setTimeout(() => {
					isVisible = false;
					progress = 0;
				}, 250);
				return () => {
					if (timer) clearInterval(timer);
					clearTimeout(timeout);
				};
			}
		}
	});
</script>

{#if isVisible}
	<div
		class="fixed inset-x-0 top-0 z-50 h-1 overflow-hidden bg-transparent"
		role="progressbar"
		aria-label="Page loading"
		aria-valuemin="0"
		aria-valuemax="100"
		aria-valuenow={Math.round(progress)}
	>
		<div
			class="h-full w-full origin-left bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-500 shadow-[0_0_10px_rgba(99,102,241,0.6)] transition-transform duration-200 ease-out"
			style="transform: scaleX({progress / 100});"
		></div>
	</div>
{/if}
