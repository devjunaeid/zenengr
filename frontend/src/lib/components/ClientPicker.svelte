<script>
	import ApiCombobox from './ApiCombobox.svelte';
	import * as clientApi from '$lib/api/clients.js';
	import { auth } from '$lib/stores/auth.svelte.js';

	/**
	 * @type {{
	 *   id?: string,
	 *   name?: string,
	 *   value?: string | null,
	 *   selectedLabel?: string | null,
	 *   selectedClient?: import('$lib/api/clients.js').ClientPickerItem | null,
	 *   placeholder?: string,
	 *   status?: string,
	 *   disabled?: boolean,
	 *   required?: boolean,
	 *   clearable?: boolean,
	 *   initialItems?: import('$lib/api/clients.js').ClientPickerItem[],
	 *   onselect?: (client: import('$lib/api/clients.js').ClientPickerItem | null) => void
	 * }}
	 */
	let {
		id = 'client-picker',
		name = 'client_id',
		value = $bindable(''),
		selectedLabel = $bindable(''),
		selectedClient = $bindable(null),
		placeholder = 'Select a client...',
		status = 'active',
		disabled = false,
		required = false,
		clearable = true,
		initialItems = [],
		onselect
	} = $props();

	function transformClientToOption(c) {
		return {
			id: c.id,
			label: c.name,
			sublabel: [c.email, c.phone].filter(Boolean).join(' • '),
			badge: c.status !== 'active' ? c.status : undefined,
			raw: c
		};
	}

	let transformedInitialItems = $derived(initialItems.map(transformClientToOption));

	async function fetchClients(query) {
		const res = await clientApi.getClientPicker(fetch, auth.token, {
			q: query || undefined,
			status: status || undefined,
			limit: 20
		});
		return (res.items || []).map(transformClientToOption);
	}

	function handleSelect(option) {
		selectedClient = option?.raw ?? null;
		onselect?.(selectedClient);
	}
</script>

<ApiCombobox
	{id}
	{name}
	bind:value
	bind:selectedLabel
	{placeholder}
	searchPlaceholder="Search client by name, email, or phone..."
	{disabled}
	{required}
	{clearable}
	initialItems={transformedInitialItems}
	fetchItems={fetchClients}
	onselect={handleSelect}
/>
