<script>
	import ApiCombobox from './ApiCombobox.svelte';
	import * as projectApi from '$lib/api/projects.js';
	import { auth } from '$lib/stores/auth.svelte.js';

	/**
	 * @type {{
	 *   id?: string,
	 *   name?: string,
	 *   value?: string | null,
	 *   selectedLabel?: string | null,
	 *   selectedProject?: import('$lib/api/projects.js').ProjectPickerItem | null,
	 *   placeholder?: string,
	 *   clientId?: string | null,
	 *   disabled?: boolean,
	 *   required?: boolean,
	 *   clearable?: boolean,
	 *   initialItems?: import('$lib/api/projects.js').ProjectPickerItem[],
	 *   onselect?: (project: import('$lib/api/projects.js').ProjectPickerItem | null) => void
	 * }}
	 */
	let {
		id = 'project-picker',
		name = 'project_id',
		value = $bindable(''),
		selectedLabel = $bindable(''),
		selectedProject = $bindable(null),
		placeholder = 'Select a project...',
		clientId = null,
		disabled = false,
		required = false,
		clearable = true,
		initialItems = [],
		onselect
	} = $props();

	function transformProjectToOption(p) {
		return {
			id: p.id,
			label: p.name,
			sublabel: p.client_name ? `Client: ${p.client_name}` : undefined,
			badge: p.status,
			raw: p
		};
	}

	let transformedInitialItems = $derived(initialItems.map(transformProjectToOption));

	async function fetchProjects(query) {
		const res = await projectApi.getProjectPicker(fetch, auth.token, {
			q: query || undefined,
			client_id: clientId || undefined,
			limit: 20
		});
		return (res.items || []).map(transformProjectToOption);
	}

	function handleSelect(option) {
		selectedProject = option?.raw ?? null;
		onselect?.(selectedProject);
	}
</script>

<ApiCombobox
	{id}
	{name}
	bind:value
	bind:selectedLabel
	{placeholder}
	searchPlaceholder="Search project by name or client..."
	{disabled}
	{required}
	{clearable}
	initialItems={transformedInitialItems}
	fetchItems={fetchProjects}
	onselect={handleSelect}
/>
