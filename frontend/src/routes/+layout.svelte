<script>
	import './layout.css';
	import { onMount } from 'svelte';
	import favicon from '$lib/assets/favicon.svg';
	import NavProgressBar from '$lib/components/NavProgressBar.svelte';
	import OfflineBanner from '$lib/components/OfflineBanner.svelte';
	import { pwa } from '$lib/stores/pwa.svelte.js';

	let { children } = $props();

	onMount(() => {
		pwa.init();
		/** @type {any} */
		const win = typeof window !== 'undefined' ? window : null;
		if (win?.dismissBootLoader) {
			win.dismissBootLoader();
		}
	});
</script>

<svelte:head>
	<link rel="icon" type="image/svg+xml" href={favicon} />
	<link rel="alternate icon" type="image/png" href="/favicon.png" />
</svelte:head>
<NavProgressBar />
<OfflineBanner />
{@render children()}
