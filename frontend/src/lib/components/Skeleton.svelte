<script>
	/**
	 * Atomic Skeleton placeholder with subtle pulse animation.
	 *
	 * @typedef {Object} Props
	 * @property {string} [class] Optional CSS classes
	 * @property {string} [rounded] Rounded radius variant ('sm' | 'md' | 'lg' | 'full' | 'none')
	 */

	let { class: className = '', rounded = 'md', ...restProps } = $props();

	const roundedClasses = {
		none: 'rounded-none',
		sm: 'rounded-sm',
		md: 'rounded-md',
		lg: 'rounded-lg',
		full: 'rounded-full'
	};
</script>

<div
	class="animate-pulse bg-slate-200 {roundedClasses[rounded] ?? 'rounded-md'} {className}"
	aria-hidden="true"
	{...restProps}
></div>
