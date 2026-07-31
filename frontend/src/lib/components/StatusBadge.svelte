<script>
	import { humanize } from '$lib/utils/format.js';

	/**
	 * Status badge with a text label AND color (color is never the sole indicator).
	 * @type {{ status: string|null|undefined }}
	 */
	let { status } = $props();

	/** @type {Record<string, string>} */
	const styles = {
		active: 'bg-green-100 text-green-800 ring-green-600/20',
		trial: 'bg-blue-100 text-blue-800 ring-blue-600/20',
		trialing: 'bg-blue-100 text-blue-800 ring-blue-600/20',
		suspended: 'bg-amber-100 text-amber-800 ring-amber-600/20',
		past_due: 'bg-red-100 text-red-800 ring-red-600/20',
		cancelled: 'bg-slate-200 text-slate-700 ring-slate-500/20',
		pending: 'bg-slate-100 text-slate-800 ring-slate-500/20',
		accepted: 'bg-green-100 text-green-800 ring-green-600/20',
		expired: 'bg-slate-200 text-slate-700 ring-slate-500/20',
		revoked: 'bg-slate-200 text-slate-700 ring-slate-500/20',
		inactive: 'bg-slate-200 text-slate-700 ring-slate-500/20',
		archived: 'bg-slate-200 text-slate-700 ring-slate-500/20',
		draft: 'bg-slate-100 text-slate-700 ring-slate-500/20',
		on_hold: 'bg-amber-100 text-amber-800 ring-amber-600/20',
		completed: 'bg-green-100 text-green-800 ring-green-600/20',
		in_progress: 'bg-blue-100 text-blue-800 ring-blue-600/20',
		blocked: 'bg-red-100 text-red-800 ring-red-600/20'
	};

	let style = $derived(styles[status ?? ''] ?? 'bg-slate-100 text-slate-800 ring-slate-500/20');
</script>

<span
	class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {style}"
>
	{humanize(status)}
</span>
