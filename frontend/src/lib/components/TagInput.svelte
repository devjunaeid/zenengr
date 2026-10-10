<script>
	import { onMount } from 'svelte';
	import Icon from '@iconify/svelte';
	import tagOutline from '@iconify-icons/mdi/tag-outline';
	import plus from '@iconify-icons/mdi/plus';
	import close from '@iconify-icons/mdi/close';
	import * as clientApi from '$lib/api/clients.js';
	import { auth } from '$lib/stores/auth.svelte.js';

	/**
	 * @type {{
	 *   id?: string,
	 *   tags?: string[],
	 *   availableTags?: string[],
	 *   placeholder?: string,
	 *   disabled?: boolean,
	 *   allowCreate?: boolean,
	 *   onchange?: (tags: string[]) => void
	 * }}
	 */
	let {
		id = 'tag-input',
		tags = $bindable([]),
		availableTags = $bindable([]),
		placeholder = 'Search existing tags or type to create...',
		disabled = false,
		allowCreate = true,
		onchange
	} = $props();

	let inputRef = $state(null);
	let containerRef = $state(null);
	let query = $state('');
	let open = $state(false);
	let activeIndex = $state(-1);
	let loading = $state(false);

	// Load tenant tags on mount if not already populated
	onMount(async () => {
		if (availableTags.length === 0 && auth.token) {
			loading = true;
			try {
				const res = await clientApi.listTags(fetch, auth.token);
				if (Array.isArray(res?.tags)) {
					// Deduplicate and sort
					const set = new Set([...availableTags, ...res.tags]);
					availableTags = Array.from(set).sort();
				}
			} catch (e) {
				console.warn('Could not load tenant tags:', e);
			} finally {
				loading = false;
			}
		}

		function handleClickOutside(e) {
			if (containerRef && !containerRef.contains(e.target)) {
				open = false;
				activeIndex = -1;
			}
		}

		document.addEventListener('mousedown', handleClickOutside);
		return () => {
			document.removeEventListener('mousedown', handleClickOutside);
		};
	});

	// Normalize tag helper
	function cleanTag(t) {
		return t.trim().replace(/^#+/, '');
	}

	function tagExists(tagList, target) {
		const norm = target.toLowerCase();
		return tagList.some((t) => t.toLowerCase() === norm);
	}

	// Filtered suggestions based on query and already-selected tags
	let filteredExisting = $derived.by(() => {
		const q = query.trim().toLowerCase();
		return availableTags.filter((t) => {
			if (tagExists(tags, t)) return false;
			if (!q) return true;
			return t.toLowerCase().includes(q);
		});
	});

	let showCreateOption = $derived.by(() => {
		if (!allowCreate) return false;
		const q = cleanTag(query);
		if (!q) return false;
		// If already in selected tags or exactly matches an existing suggestion, don't show "Create"
		if (tagExists(tags, q)) return false;
		return !availableTags.some((t) => t.toLowerCase() === q.toLowerCase());
	});

	// Full list of dropdown items (existing matches + optional create option)
	let dropdownItems = $derived.by(() => {
		const items = [];
		for (const t of filteredExisting) {
			items.push({ type: 'existing', value: t });
		}
		if (showCreateOption) {
			items.push({ type: 'create', value: cleanTag(query) });
		}
		return items;
	});

	function addTag(value) {
		const val = cleanTag(value);
		if (!val) return;
		if (!tagExists(tags, val)) {
			const next = [...tags, val];
			tags = next;
			onchange?.(next);
		}
		// Also add to availableTags so it's reusable across this workspace
		if (!availableTags.some((t) => t.toLowerCase() === val.toLowerCase())) {
			availableTags = [...availableTags, val].sort();
		}
		query = '';
		activeIndex = -1;
		open = false;
		inputRef?.focus();
	}

	function removeTag(value) {
		if (disabled) return;
		const next = tags.filter((t) => t.toLowerCase() !== value.toLowerCase());
		tags = next;
		onchange?.(next);
	}

	function handleKeydown(e) {
		if (disabled) return;

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (!open) {
				open = true;
				activeIndex = 0;
			} else {
				activeIndex = activeIndex < dropdownItems.length - 1 ? activeIndex + 1 : 0;
			}
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (!open) {
				open = true;
				activeIndex = dropdownItems.length - 1;
			} else {
				activeIndex = activeIndex > 0 ? activeIndex - 1 : dropdownItems.length - 1;
			}
		} else if (e.key === 'Enter' || e.key === ',') {
			e.preventDefault();
			e.stopPropagation();

			if (open && activeIndex >= 0 && activeIndex < dropdownItems.length) {
				const item = dropdownItems[activeIndex];
				addTag(item.value);
			} else if (query.trim()) {
				// Direct Enter on typed query
				addTag(query);
			}
		} else if (e.key === 'Backspace' && !query && tags.length > 0) {
			// Remove last tag
			removeTag(tags[tags.length - 1]);
		} else if (e.key === 'Escape') {
			open = false;
			activeIndex = -1;
		}
	}

	function handleInput(e) {
		query = e.currentTarget.value;
		if (query.includes(',')) {
			const parts = query.split(',').map(cleanTag).filter(Boolean);
			for (const p of parts) {
				addTag(p);
			}
			query = '';
			return;
		}
		open = true;
		activeIndex = 0;
	}

	function handleFocus() {
		open = true;
	}
</script>

<div class="w-full space-y-2" bind:this={containerRef}>
	<!-- Selected Tags Chips Display (On Top of Input) -->
	{#if tags.length > 0}
		<div class="flex flex-wrap items-center gap-1.5 pb-0.5">
			{#each tags as t (t)}
				<span
					class="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 ring-1 ring-indigo-200 transition-colors"
				>
					<Icon icon={tagOutline} class="h-3 w-3 text-indigo-500" />
					<span>{t}</span>
					{#if !disabled}
						<button
							type="button"
							onclick={() => removeTag(t)}
							aria-label={`Remove tag ${t}`}
							class="rounded text-indigo-400 hover:bg-indigo-100 hover:text-indigo-800 focus:outline-none"
						>
							<Icon icon={close} class="h-3 w-3" />
						</button>
					{/if}
				</span>
			{/each}
			<span class="text-xs text-slate-400">
				({tags.length}
				{tags.length === 1 ? 'tag' : 'tags'} selected)
			</span>
		</div>
	{/if}

	<!-- Search & Input Box with Dropdown -->
	<div class="relative">
		<div
			class="flex min-h-[42px] w-full items-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 shadow-2xs transition-colors focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 {disabled
				? 'cursor-not-allowed bg-slate-50'
				: ''}"
		>
			<div class="mr-2 flex shrink-0 items-center text-slate-400">
				<Icon icon={tagOutline} class="h-4 w-4" />
			</div>

			<input
				{id}
				bind:this={inputRef}
				type="text"
				value={query}
				oninput={handleInput}
				onfocus={handleFocus}
				onkeydown={handleKeydown}
				{placeholder}
				{disabled}
				autocomplete="off"
				class="w-full border-0 bg-transparent p-0 text-sm text-slate-900 placeholder-slate-400 focus:ring-0 focus:outline-none disabled:cursor-not-allowed"
			/>

			{#if query}
				<button
					type="button"
					onclick={() => {
						query = '';
						open = false;
						activeIndex = -1;
					}}
					aria-label="Clear input"
					class="ml-1 text-slate-400 hover:text-slate-600"
				>
					<Icon icon={close} class="h-4 w-4" />
				</button>
			{/if}

			{#if loading}
				<span class="ml-2 text-xs text-slate-400">Loading…</span>
			{/if}
		</div>

		<!-- Dropdown Suggestions Menu -->
		{#if open && !disabled && (dropdownItems.length > 0 || loading)}
			<div
				class="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1.5 shadow-lg ring-1 ring-black/5"
				role="listbox"
			>
				{#if filteredExisting.length > 0}
					<div class="px-3 py-1 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
						Reusable Tenant Tags
					</div>
					{#each dropdownItems.filter((i) => i.type === 'existing') as item (item.value)}
						{@const isSelected = activeIndex === dropdownItems.indexOf(item)}
						<button
							type="button"
							role="option"
							aria-selected={isSelected}
							onmouseenter={() => (activeIndex = dropdownItems.indexOf(item))}
							onclick={() => addTag(item.value)}
							class="flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors {isSelected
								? 'bg-indigo-50 font-medium text-indigo-900'
								: 'text-slate-700 hover:bg-slate-50'}"
						>
							<span class="flex items-center gap-2">
								<Icon icon={tagOutline} class="h-3.5 w-3.5 text-indigo-500" />
								<span>{item.value}</span>
							</span>
							<span class="text-xs text-slate-400">Select</span>
						</button>
					{/each}
				{/if}

				{#if showCreateOption}
					{#each dropdownItems.filter((i) => i.type === 'create') as item (item.value)}
						{@const isSelected = activeIndex === dropdownItems.indexOf(item)}
						<div class="mt-1 border-t border-slate-100 pt-1">
							<button
								type="button"
								role="option"
								aria-selected={isSelected}
								onmouseenter={() => (activeIndex = dropdownItems.indexOf(item))}
								onclick={() => addTag(item.value)}
								class="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium transition-colors {isSelected
									? 'bg-indigo-600 text-white'
									: 'bg-indigo-50/50 text-indigo-700 hover:bg-indigo-50'}"
							>
								<span class="flex items-center gap-2">
									<Icon icon={plus} class="h-4 w-4" />
									<span>Create new tag: <strong>"{item.value}"</strong></span>
								</span>
								<span class="text-xs opacity-75">Press Enter</span>
							</button>
						</div>
					{/each}
				{/if}

				{#if dropdownItems.length === 0 && !loading}
					<div class="px-3 py-3 text-center text-xs text-slate-500">
						No matching tags found. Type and press <kbd
							class="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px] text-slate-600"
							>Enter</kbd
						> to create.
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
