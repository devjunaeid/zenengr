<script>
	import { pwa } from '$lib/stores/pwa.svelte.js';
	import Icon from '@iconify/svelte';
	import wifiOffIcon from '@iconify-icons/mdi/wifi-off';
	import checkCircleOutline from '@iconify-icons/mdi/check-circle-outline';

	let wasOffline = $state(false);
	let showReconnected = $state(false);
	/** @type {ReturnType<typeof setTimeout>|null} */
	let reconnectTimer = null;

	$effect(() => {
		if (!pwa.isOnline) {
			wasOffline = true;
			showReconnected = false;
			if (reconnectTimer) clearTimeout(reconnectTimer);
		} else if (wasOffline) {
			// Just transitioned from offline to online
			showReconnected = true;
			wasOffline = false;
			if (reconnectTimer) clearTimeout(reconnectTimer);
			reconnectTimer = setTimeout(() => {
				showReconnected = false;
			}, 3000);
		}
		return () => {
			if (reconnectTimer) clearTimeout(reconnectTimer);
		};
	});
</script>

{#if !pwa.isOnline}
	<div
		class="fixed bottom-4 left-1/2 z-[9999] -translate-x-1/2 transform transition-all duration-300 ease-out"
		role="status"
		aria-live="polite"
	>
		<div
			class="flex items-center gap-2.5 rounded-full border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-900 shadow-lg shadow-amber-950/10 backdrop-blur"
		>
			<Icon icon={wifiOffIcon} class="h-4 w-4 animate-pulse text-amber-600" />
			<span>You are offline. Reconnecting when connection resumes...</span>
		</div>
	</div>
{:else if showReconnected}
	<div
		class="fixed bottom-4 left-1/2 z-[9999] -translate-x-1/2 transform transition-all duration-300 ease-out"
		role="status"
		aria-live="polite"
	>
		<div
			class="flex items-center gap-2.5 rounded-full border border-emerald-300 bg-emerald-50 px-4 py-2 text-xs font-semibold text-emerald-900 shadow-lg shadow-emerald-950/10 backdrop-blur"
		>
			<Icon icon={checkCircleOutline} class="h-4 w-4 text-emerald-600" />
			<span>Back online. Reconnected.</span>
		</div>
	</div>
{/if}
