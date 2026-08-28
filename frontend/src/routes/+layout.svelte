<script>
	import './layout.css';
	import { onMount } from 'svelte';
	import favicon from '$lib/assets/favicon.svg';
	import NavProgressBar from '$lib/components/NavProgressBar.svelte';

	let { children } = $props();

	onMount(() => {
		if (typeof window !== 'undefined' && window.dismissBootLoader) {
			window.dismissBootLoader();
		}
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<NavProgressBar />
{@render children()}
