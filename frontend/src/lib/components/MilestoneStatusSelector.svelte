<script>
	/**
	 * 4-state milestone status selector.
	 *
	 * Native <select> for keyboard reach. The currently-selected value is
	 * accompanied by a small color swatch so status is never communicated by
	 * color alone (text label is also rendered).
	 *
	 * @type {{
	 *   value: 'pending'|'in_progress'|'completed'|'blocked',
	 *   onchange: (next: 'pending'|'in_progress'|'completed'|'blocked') => Promise<void> | void,
	 *   busy?: boolean,
	 *   disabled?: boolean,
	 *   id?: string
	 * }}
	 */
	let { value, onchange, busy = false, disabled = false, id = 'milestone-status' } = $props();

	/** @type {Array<{ key: 'pending'|'in_progress'|'completed'|'blocked', label: string, dot: string, select: string }>} */
	const options = [
		{
			key: 'pending',
			label: 'Pending',
			dot: 'bg-slate-400',
			select: 'bg-slate-100 text-slate-800 ring-slate-500/20'
		},
		{
			key: 'in_progress',
			label: 'In progress',
			dot: 'bg-blue-500',
			select: 'bg-blue-100 text-blue-800 ring-blue-600/20'
		},
		{
			key: 'completed',
			label: 'Completed',
			dot: 'bg-green-500',
			select: 'bg-green-100 text-green-800 ring-green-600/20'
		},
		{
			key: 'blocked',
			label: 'Blocked',
			dot: 'bg-red-500',
			select: 'bg-red-100 text-red-800 ring-red-600/20'
		}
	];

	let current = $derived(options.find((o) => o.key === value) ?? options[0]);
	let isDisabled = $derived(Boolean(busy) || Boolean(disabled));

	/**
	 * @param {Event & { currentTarget: HTMLSelectElement }} e
	 */
	async function handleChange(e) {
		const next = /** @type {'pending'|'in_progress'|'completed'|'blocked'} */ (
			e.currentTarget.value
		);
		await onchange(next);
	}
</script>

<span class="inline-flex max-w-full flex-wrap items-center gap-2" data-status={value}>
	<span
		class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {current.select}"
		aria-hidden="true"
	>
		<span class="h-1.5 w-1.5 rounded-full {current.dot}"></span>
		{current.label}
	</span>
	<label for={id} class="sr-only">Change status</label>
	<select
		{id}
		{value}
		disabled={isDisabled}
		aria-busy={busy}
		onchange={handleChange}
		class="max-w-full min-w-0 rounded-md border-slate-300 text-xs shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
	>
		{#each options as opt (opt.key)}
			<option value={opt.key}>{opt.label}</option>
		{/each}
	</select>
</span>
