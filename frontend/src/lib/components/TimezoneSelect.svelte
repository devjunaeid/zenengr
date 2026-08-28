<script>
	import { onMount } from 'svelte';

	let { value = $bindable('UTC'), disabled = false, id = 'timezone-select' } = $props();

	let open = $state(false);
	let search = $state('');
	let containerRef = $state(null);
	let inputRef = $state(null);

	// Get formatted offset for a timezone (e.g. "UTC+06:00")
	function getTimezoneOffset(tz) {
		try {
			const now = new Date();
			const formatter = new Intl.DateTimeFormat('en-US', {
				timeZone: tz,
				timeZoneName: 'shortOffset'
			});
			const parts = formatter.formatToParts(now);
			const tzPart = parts.find((p) => p.type === 'timeZoneName')?.value;
			if (tzPart && tzPart.startsWith('GMT')) {
				return tzPart.replace('GMT', 'UTC');
			}
			return tzPart || 'UTC';
		} catch {
			return 'UTC';
		}
	}

	// Generate timezone list
	const TIMEZONE_LIST = (() => {
		let list = [];
		try {
			if (typeof Intl !== 'undefined' && typeof Intl.supportedValuesOf === 'function') {
				list = Intl.supportedValuesOf('timeZone');
			}
		} catch {
			// fallback
		}

		if (!list || list.length === 0) {
			list = [
				'UTC',
				'America/New_York',
				'America/Chicago',
				'America/Denver',
				'America/Los_Angeles',
				'America/Toronto',
				'America/Sao_Paulo',
				'Europe/London',
				'Europe/Paris',
				'Europe/Berlin',
				'Europe/Rome',
				'Europe/Madrid',
				'Europe/Amsterdam',
				'Europe/Warsaw',
				'Asia/Dubai',
				'Asia/Karachi',
				'Asia/Kolkata',
				'Asia/Dhaka',
				'Asia/Bangkok',
				'Asia/Singapore',
				'Asia/Hong_Kong',
				'Asia/Tokyo',
				'Asia/Seoul',
				'Asia/Shanghai',
				'Australia/Sydney',
				'Australia/Melbourne',
				'Pacific/Auckland',
				'Pacific/Honolulu'
			];
		}

		if (!list.includes('UTC')) {
			list.unshift('UTC');
		}

		return list.map((tz) => {
			const offset = getTimezoneOffset(tz);
			const cleanName = tz.replace(/_/g, ' ');
			return {
				id: tz,
				label: `(${offset}) ${cleanName}`,
				offset,
				cleanName,
				searchTerms: `${tz} ${cleanName} ${offset}`.toLowerCase()
			};
		});
	})();

	let filteredTimezones = $derived(
		search.trim()
			? TIMEZONE_LIST.filter((t) => t.searchTerms.includes(search.toLowerCase().trim()))
			: TIMEZONE_LIST
	);

	let selectedItem = $derived(
		TIMEZONE_LIST.find((t) => t.id === value) || {
			id: value || 'UTC',
			label: `(${getTimezoneOffset(value || 'UTC')}) ${(value || 'UTC').replace(/_/g, ' ')}`
		}
	);

	function selectTimezone(tzId) {
		value = tzId;
		open = false;
		search = '';
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') {
			open = false;
		}
	}

	function handleClickOutside(e) {
		if (containerRef && !containerRef.contains(e.target)) {
			open = false;
		}
	}

	onMount(() => {
		document.addEventListener('click', handleClickOutside);
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="relative w-full max-w-sm" bind:this={containerRef} onkeydown={handleKeydown}>
	<button
		type="button"
		{id}
		{disabled}
		aria-haspopup="listbox"
		aria-expanded={open}
		onclick={() => {
			if (!disabled) {
				open = !open;
				if (open) {
					setTimeout(() => inputRef?.focus(), 50);
				}
			}
		}}
		class="flex w-full items-center justify-between rounded-lg border border-slate-300 bg-white px-3 py-2 text-left text-sm shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-60"
	>
		<span class="truncate font-medium text-slate-800">
			{selectedItem.label}
		</span>
		<svg
			class="ml-2 h-4 w-4 shrink-0 text-slate-400 transition-transform {open ? 'rotate-180' : ''}"
			viewBox="0 0 20 20"
			fill="currentColor"
		>
			<path
				fill-rule="evenodd"
				d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
				clip-rule="evenodd"
			/>
		</svg>
	</button>

	{#if open}
		<div
			class="absolute z-50 mt-1 max-h-72 w-full min-w-[320px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
		>
			<!-- Search Box -->
			<div class="border-b border-slate-100 p-2 bg-slate-50">
				<div class="relative">
					<input
						bind:this={inputRef}
						type="text"
						bind:value={search}
						placeholder="Search city, country, or UTC..."
						class="w-full rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
					/>
					{#if search}
						<button
							type="button"
							onclick={() => (search = '')}
							class="absolute right-2 top-1.5 text-xs text-slate-400 hover:text-slate-600"
						>
							×
						</button>
					{/if}
				</div>
			</div>

			<!-- Options List -->
			<ul
				role="listbox"
				tabindex="-1"
				class="max-h-56 overflow-y-auto divide-y divide-slate-50 p-1 text-xs"
			>
				{#if filteredTimezones.length === 0}
					<li class="p-3 text-center text-slate-400">No timezones found</li>
				{:else}
					{#each filteredTimezones as tz (tz.id)}
						<li>
							<button
								type="button"
								role="option"
								aria-selected={tz.id === value}
								onclick={() => selectTimezone(tz.id)}
								class="flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left hover:bg-indigo-50/70 hover:text-indigo-900 transition-colors {tz.id ===
								value
									? 'bg-indigo-50 font-semibold text-indigo-700'
									: 'text-slate-700'}"
							>
								<span class="truncate">{tz.label}</span>
								{#if tz.id === value}
									<span class="text-indigo-600 font-bold ml-2">✓</span>
								{/if}
							</button>
						</li>
					{/each}
				{/if}
			</ul>
		</div>
	{/if}
</div>
