<script>
	/**
	 * Accessible switch for boolean preferences (e.g. per-event notification
	 * toggles). Rendered as a button with role="switch"; click, Space, and
	 * Enter all toggle. The parent owns the checked state and is notified via
	 * `onchange(checked)` with the new value.
	 * @type {{
	 *   checked: boolean,
	 *   disabled?: boolean,
	 *   onchange: (checked: boolean) => void,
	 *   label: string
	 * }}
	 */
	let { checked, disabled = false, onchange, label } = $props();

	function handleToggle() {
		if (disabled) return;
		onchange(!checked);
	}
</script>

<button
	type="button"
	role="switch"
	aria-checked={checked}
	aria-label={label}
	{disabled}
	onclick={handleToggle}
	class="inline-flex rounded-full focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none {disabled
		? 'cursor-not-allowed opacity-60'
		: 'cursor-pointer'}"
>
	<span
		class="relative block h-5 w-9 rounded-full transition-colors {checked
			? 'bg-indigo-600'
			: 'bg-slate-300'}"
	>
		<span
			class="absolute top-0.5 left-0.5 block h-4 w-4 rounded-full bg-white shadow transition-transform {checked
				? 'translate-x-4'
				: 'translate-x-0'}"
		></span>
	</span>
</button>
