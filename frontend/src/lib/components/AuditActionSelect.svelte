<script>
	import { onMount } from 'svelte';
	import Icon from '@iconify/svelte';
	import chevronDown from '@iconify-icons/mdi/chevron-down';
	import magnify from '@iconify-icons/mdi/magnify';
	import check from '@iconify-icons/mdi/check';
	import { TENANT_AUDIT_ACTION_OPTIONS, auditActionLabel, auditGroup, groupIcon } from '$lib/utils/audit.js';

	let { value = $bindable(''), disabled = false, id = 'audit-action-select', placeholder = 'All system actions' } = $props();

	let open = $state(false);
	let search = $state('');
	let containerRef = $state(null);
	let inputRef = $state(null);

	// Flatten options for lookup
	const ALL_OPTIONS = (() => {
		const list = [];
		for (const g of TENANT_AUDIT_ACTION_OPTIONS) {
			for (const item of g.items) {
				list.push({
					value: item.value,
					label: item.label,
					group: g.group,
					searchText: `${item.label} ${item.value} ${g.group}`.toLowerCase()
				});
			}
		}
		return list;
	})();

	let selectedMeta = $derived(
		value ? ALL_OPTIONS.find((o) => o.value === value) || { value, label: auditActionLabel(value), group: auditGroup(value) } : null
	);

	let filteredGroups = $derived.by(() => {
		const q = search.toLowerCase().trim();
		if (!q) return TENANT_AUDIT_ACTION_OPTIONS;

		const out = [];
		for (const g of TENANT_AUDIT_ACTION_OPTIONS) {
			const groupMatch = g.group.toLowerCase().includes(q);
			const matchingItems = g.items.filter(
				(item) => groupMatch || item.label.toLowerCase().includes(q) || item.value.toLowerCase().includes(q)
			);
			if (matchingItems.length > 0) {
				out.push({ group: g.group, items: matchingItems });
			}
		}
		return out;
	});

	function toggleDropdown() {
		if (disabled) return;
		open = !open;
		if (open) {
			search = '';
			setTimeout(() => {
				if (inputRef) inputRef.focus();
			}, 50);
		}
	}

	function selectOption(val) {
		value = val;
		open = false;
		search = '';
	}

	onMount(() => {
		function handleClickOutside(e) {
			if (containerRef && !containerRef.contains(e.target)) {
				open = false;
			}
		}
		function handleKeyDown(e) {
			if (e.key === 'Escape' && open) {
				open = false;
			}
		}
		document.addEventListener('mousedown', handleClickOutside);
		document.addEventListener('keydown', handleKeyDown);
		return () => {
			document.removeEventListener('mousedown', handleClickOutside);
			document.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

<div class="relative w-full" bind:this={containerRef}>
	<!-- Trigger Button -->
	<button
		type="button"
		{id}
		{disabled}
		aria-haspopup="listbox"
		aria-expanded={open}
		onclick={toggleDropdown}
		class="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white py-2 px-3 text-left text-xs font-medium text-slate-800 shadow-2xs transition-colors hover:border-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-400"
	>
		<span class="truncate">
			{#if selectedMeta}
				<span class="inline-flex items-center gap-1.5">
					<Icon icon={groupIcon(selectedMeta.group)} class="h-3.5 w-3.5 text-indigo-600 shrink-0" />
					<span class="font-semibold text-slate-900">{selectedMeta.label}</span>
					<span class="text-[11px] text-slate-400">({selectedMeta.group})</span>
				</span>
			{:else}
				<span class="text-slate-500">{placeholder}</span>
			{/if}
		</span>
		<Icon
			icon={chevronDown}
			class="h-4 w-4 text-slate-400 shrink-0 transition-transform duration-150 {open ? 'rotate-180 text-indigo-600' : ''}"
		/>
	</button>

	<!-- Dropdown Popover -->
	{#if open}
		<div
			class="absolute left-0 top-full z-50 mt-1.5 max-h-80 w-full min-w-[320px] max-w-[90vw] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl ring-1 ring-black/5 animate-fade-in"
		>
			<!-- Search Header -->
			<div class="border-b border-slate-100 p-2.5 bg-slate-50/70">
				<div class="relative">
					<Icon icon={magnify} class="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
					<input
						type="text"
						bind:this={inputRef}
						bind:value={search}
						placeholder="Search actions (e.g. invoice, project, user)..."
						class="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					/>
				</div>
			</div>

			<!-- Options List -->
			<div class="max-h-60 overflow-y-auto divide-y divide-slate-100 p-1">
				<!-- Reset Option -->
				<button
					type="button"
					onclick={() => selectOption('')}
					class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs font-semibold transition-colors {value === ''
						? 'bg-indigo-50 text-indigo-700'
						: 'text-slate-700 hover:bg-slate-50'}"
				>
					<span>All system actions</span>
					{#if value === ''}
						<Icon icon={check} class="h-4 w-4 text-indigo-600 shrink-0" />
					{/if}
				</button>

				{#if filteredGroups.length === 0}
					<div class="py-6 text-center text-xs text-slate-400">
						No actions match "{search}"
					</div>
				{:else}
					{#each filteredGroups as group (group.group)}
						<div class="py-1">
							<div class="flex items-center gap-1.5 px-3 py-1 text-[11px] font-bold tracking-wider uppercase text-slate-400">
								<Icon icon={groupIcon(group.group)} class="h-3 w-3 text-slate-400" />
								<span>{group.group}</span>
							</div>

							{#each group.items as item (item.value)}
								{@const selected = value === item.value}
								<button
									type="button"
									onclick={() => selectOption(item.value)}
									class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition-colors {selected
										? 'bg-indigo-50 font-bold text-indigo-700'
										: 'text-slate-700 hover:bg-slate-100/70'}"
								>
									<span class="truncate">{item.label}</span>
									{#if selected}
										<Icon icon={check} class="h-4 w-4 text-indigo-600 shrink-0 ml-2" />
									{/if}
								</button>
							{/each}
						</div>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>
