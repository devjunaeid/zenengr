<script>
	import { onMount, tick } from 'svelte';
	import Icon from '@iconify/svelte';
	import chevronDown from '@iconify-icons/mdi/chevron-down';
	import magnify from '@iconify-icons/mdi/magnify';
	import close from '@iconify-icons/mdi/close';
	import check from '@iconify-icons/mdi/check';
	import Spinner from '$lib/components/Spinner.svelte';

	/**
	 * @typedef {Object} ComboboxOption
	 * @property {string} id
	 * @property {string} label
	 * @property {string} [sublabel]
	 * @property {string} [badge]
	 * @property {any} [raw]
	 */

	/**
	 * @type {{
	 *   id?: string,
	 *   name?: string,
	 *   value?: string | null,
	 *   selectedLabel?: string | null,
	 *   selectedItem?: any | null,
	 *   placeholder?: string,
	 *   searchPlaceholder?: string,
	 *   disabled?: boolean,
	 *   required?: boolean,
	 *   clearable?: boolean,
	 *   initialItems?: ComboboxOption[],
	 *   fetchItems: (query: string) => Promise<ComboboxOption[]>,
	 *   onselect?: (item: ComboboxOption | null) => void
	 * }}
	 */
	let {
		id = 'api-combobox',
		name = '',
		value = $bindable(''),
		selectedLabel = $bindable(''),
		selectedItem = $bindable(null),
		placeholder = 'Select an option...',
		searchPlaceholder = 'Type to search...',
		disabled = false,
		required = false,
		clearable = true,
		initialItems = [],
		fetchItems,
		onselect
	} = $props();

	let open = $state(false);
	let query = $state('');
	let loading = $state(false);
	/** @type {ComboboxOption[]} */
	let items = $state([...initialItems]);
	/** @type {HTMLElement | null} */
	let containerRef = $state(null);
	/** @type {HTMLInputElement | null} */
	let searchInputRef = $state(null);
	/** @type {any} */
	let debounceTimer = null;

	// Synchronize display label if initialItems or value changed
	$effect(() => {
		if (value && !selectedLabel) {
			const found = items.find((i) => i.id === value);
			if (found) {
				selectedLabel = found.label;
				selectedItem = found.raw ?? found;
			}
		}
	});

	async function openDropdown() {
		if (disabled) return;
		open = true;
		if (items.length === 0) {
			await executeSearch('');
		}
		await tick();
		searchInputRef?.focus();
	}

	function closeDropdown() {
		open = false;
		query = '';
	}

	function toggleDropdown() {
		if (open) {
			closeDropdown();
		} else {
			openDropdown();
		}
	}

	async function executeSearch(q) {
		loading = true;
		try {
			const results = await fetchItems(q);
			items = results;
		} catch (err) {
			console.error('ApiCombobox search error:', err);
			items = [];
		} finally {
			loading = false;
		}
	}

	function onSearchInput(e) {
		query = e.currentTarget.value;
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			executeSearch(query.trim());
		}, 250);
	}

	function selectOption(item) {
		value = item.id;
		selectedLabel = item.label;
		selectedItem = item.raw ?? item;
		closeDropdown();
		onselect?.(item);
	}

	function clearSelection(e) {
		e.stopPropagation();
		value = '';
		selectedLabel = '';
		selectedItem = null;
		onselect?.(null);
	}

	function handleKeyDown(e) {
		if (!open) return;
		if (e.key === 'Escape') {
			closeDropdown();
		}
	}

	function handleClickOutside(e) {
		if (containerRef && !containerRef.contains(e.target)) {
			closeDropdown();
		}
	}

	onMount(() => {
		document.addEventListener('mousedown', handleClickOutside);
		document.addEventListener('keydown', handleKeyDown);
		return () => {
			document.removeEventListener('mousedown', handleClickOutside);
			document.removeEventListener('keydown', handleKeyDown);
			if (debounceTimer) clearTimeout(debounceTimer);
		};
	});
</script>

<div class="relative w-full" bind:this={containerRef}>
	<!-- Hidden input for standard HTML form submission and validation -->
	{#if name}
		<input type="hidden" {name} {value} {required} data-item={selectedItem ? '1' : '0'} />
	{/if}

	<!-- Trigger Button (Matches Admin Style) -->
	<button
		type="button"
		{id}
		{disabled}
		aria-haspopup="listbox"
		aria-expanded={open}
		onclick={toggleDropdown}
		class="flex w-full items-center justify-between gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm shadow-sm transition-colors hover:border-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
	>
		<span class="truncate {value ? 'font-medium text-slate-900' : 'text-slate-500'}">
			{selectedLabel || placeholder}
		</span>

		<div class="flex items-center gap-1">
			{#if clearable && value && !disabled}
				<button
					type="button"
					aria-label="Clear selection"
					onclick={clearSelection}
					class="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none"
				>
					<Icon icon={close} class="h-3.5 w-3.5" />
				</button>
			{/if}
			<Icon
				icon={chevronDown}
				class="h-4 w-4 shrink-0 text-slate-400 transition-transform duration-150 {open
					? 'rotate-180 text-indigo-600'
					: ''}"
			/>
		</div>
	</button>

	<!-- Popover Dropdown (Matches Admin Style) -->
	{#if open}
		<div
			class="absolute top-full left-0 z-50 mt-1.5 max-h-80 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl ring-1 ring-black/5"
			role="listbox"
		>
			<!-- Search Input Box -->
			<div class="border-b border-slate-100 bg-slate-50/70 p-2.5">
				<div class="relative">
					<Icon icon={magnify} class="absolute top-2.5 left-2.5 h-4 w-4 text-slate-400" />
					<input
						type="text"
						aria-label={searchPlaceholder}
						bind:this={searchInputRef}
						value={query}
						oninput={onSearchInput}
						placeholder={searchPlaceholder}
						class="w-full rounded-lg border border-slate-200 bg-white py-1.5 pr-8 pl-8 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
					/>
					{#if query}
						<button
							type="button"
							aria-label="Clear search"
							onclick={() => {
								query = '';
								executeSearch('');
							}}
							class="absolute top-2 right-2 rounded p-0.5 text-slate-400 hover:text-slate-600"
						>
							<Icon icon={close} class="h-3.5 w-3.5" />
						</button>
					{/if}
				</div>
			</div>

			<!-- Options List -->
			<div class="max-h-60 overflow-y-auto p-1">
				{#if loading}
					<div class="flex items-center justify-center gap-2 py-4 text-xs text-slate-500">
						<Spinner class="h-4 w-4 text-indigo-600" />
						<span>Searching...</span>
					</div>
				{:else if items.length === 0}
					<div class="py-4 text-center text-xs text-slate-500">
						{query ? `No matches found for "${query}"` : 'No options available'}
					</div>
				{:else}
					{#each items as item (item.id)}
						<button
							type="button"
							role="option"
							aria-selected={item.id === value}
							onclick={() => selectOption(item)}
							class="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-xs transition-colors hover:bg-indigo-50/60 {item.id ===
							value
								? 'bg-indigo-50 font-semibold text-indigo-900'
								: 'text-slate-700'}"
						>
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<span class="truncate font-medium text-slate-900">{item.label}</span>
									{#if item.badge}
										<span
											class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 capitalize"
										>
											{item.badge}
										</span>
									{/if}
								</div>
								{#if item.sublabel}
									<div class="mt-0.5 truncate text-[11px] text-slate-500">
										{item.sublabel}
									</div>
								{/if}
							</div>
							{#if item.id === value}
								<Icon icon={check} class="h-4 w-4 shrink-0 text-indigo-600" />
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>
