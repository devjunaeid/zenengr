<script>
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import NavProgressBar from '$lib/components/NavProgressBar.svelte';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<NavProgressBar />
{@render children()}
