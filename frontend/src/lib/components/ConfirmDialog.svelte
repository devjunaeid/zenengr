<script>
	import { Dialog } from 'bits-ui';
	import Spinner from './Spinner.svelte';

	/**
	 * Confirmation dialog (bits-ui Dialog). Focus is trapped; Escape closes.
	 * @type {{
	 *   open: boolean,
	 *   title: string,
	 *   description?: string,
	 *   confirmLabel?: string,
	 *   destructive?: boolean,
	 *   busy?: boolean,
	 *   onconfirm: () => void
	 * }}
	 */
	let {
		open = $bindable(false),
		title,
		description = '',
		confirmLabel = 'Confirm',
		destructive = false,
		busy = false,
		onconfirm
	} = $props();
</script>

<Dialog.Root open={open} onOpenChange={(o) => (open = o)}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold text-slate-900">{title}</Dialog.Title>
			{#if description}
				<Dialog.Description class="mt-2 text-sm text-slate-600">{description}</Dialog.Description>
			{/if}
			<div class="mt-6 flex justify-end gap-3">
				<Dialog.Close
					class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Cancel
				</Dialog.Close>
				<button
					type="button"
					disabled={busy}
					aria-busy={busy}
					onclick={() => onconfirm()}
					class="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 {destructive
						? 'bg-red-600 hover:bg-red-700'
						: 'bg-indigo-600 hover:bg-indigo-700'}"
				>
					{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
					{confirmLabel}
				</button>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
