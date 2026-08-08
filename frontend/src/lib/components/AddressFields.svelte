<script>
	import { ADDRESS_KEYS } from '$lib/utils/address.js';

	/**
	 * Structured billing address inputs (all optional). Mutates a bindable
	 * `fields` object of type AddressFields.
	 * @type {{
	 *   fields: import('$lib/utils/address.js').AddressFields,
	 *   idPrefix?: string
	 * }}
	 */
	let { fields = $bindable(), idPrefix = 'b' } = $props();

	/** @type {Record<string, string>} */
	const LABELS = {
		address_line1: 'Address line 1',
		address_line2: 'Address line 2 (optional)',
		city: 'City',
		state: 'State',
		postal_code: 'ZIP / Postal code',
		country: 'Country'
	};

	/** @type {Record<string, 'address-line1'|'address-line2'|'address-level1'|'address-level2'|'postal-code'|'country-name'>} */
	const AUTOCOMPLETE = {
		address_line1: 'address-line1',
		address_line2: 'address-line2',
		city: 'address-level2',
		state: 'address-level1',
		postal_code: 'postal-code',
		country: 'country-name'
	};
</script>

<div class="grid gap-4 sm:grid-cols-2">
	{#each ADDRESS_KEYS as key (key)}
		<div class={key === 'address_line1' || key === 'address_line2' ? 'sm:col-span-2' : ''}>
			<label for="{idPrefix}-addr-{key}" class="block text-sm font-medium text-slate-700"
				>{LABELS[key]}</label
			>
			<input
				id="{idPrefix}-addr-{key}"
				type="text"
				autocomplete={AUTOCOMPLETE[key]}
				bind:value={fields[key]}
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>
	{/each}
</div>
