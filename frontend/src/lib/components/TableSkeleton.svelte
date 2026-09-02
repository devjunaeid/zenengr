<script>
	import Skeleton from './Skeleton.svelte';

	/**
	 * @typedef {Object} Props
	 * @property {number} [rows] Number of skeleton rows to display (default: 5)
	 * @property {number} [columns] Number of columns to display (default: 4)
	 * @property {boolean} [showHeader] Show search/filter header bar placeholder (default: true)
	 * @property {string} [class] Additional container classes
	 */

	let { rows = 5, columns = 4, showHeader = true, class: className = '' } = $props();
</script>

<div class="space-y-4 {className}">
	{#if showHeader}
		<!-- Header Toolbar Placeholder -->
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div class="flex flex-wrap items-center gap-3">
				<Skeleton class="h-9 w-full rounded-lg sm:w-64" />
				<Skeleton class="h-9 w-32 rounded-lg" />
			</div>
			<div class="flex items-center gap-2">
				<Skeleton class="h-9 w-28 rounded-lg" />
				<Skeleton class="h-9 w-24 rounded-lg" />
			</div>
		</div>
	{/if}

	<!-- Table Card Container -->
	<div
		class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900"
	>
		<div class="relative overflow-x-auto">
			<table class="w-full text-left text-sm">
				<thead
					class="border-b border-slate-100 bg-slate-50/75 dark:border-slate-800/60 dark:bg-slate-800/30"
				>
					<tr>
						<!-- eslint-disable-next-line no-unused-vars -- skeleton placeholder loop; item unused -->
						{#each Array(columns) as _, i (i)}
							<th class="px-6 py-3.5">
								<Skeleton
									class="h-4 {i === 0 ? 'w-28' : i === columns - 1 ? 'ml-auto w-16' : 'w-20'}"
								/>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-100 dark:divide-slate-800/50">
					<!-- eslint-disable-next-line no-unused-vars -- skeleton placeholder loop; item unused -->
					{#each Array(rows) as _, rowIndex (rowIndex)}
						<tr class="transition-colors">
							<!-- eslint-disable-next-line no-unused-vars -- skeleton placeholder loop; item unused -->
							{#each Array(columns) as _, colIndex (colIndex)}
								<td class="px-6 py-4">
									{#if colIndex === 0}
										<!-- Primary cell: Avatar + Name / Title -->
										<div class="flex items-center gap-3">
											<Skeleton class="h-9 w-9 shrink-0 rounded-full" />
											<div class="space-y-1.5">
												<Skeleton class="h-4 {rowIndex % 2 === 0 ? 'w-36' : 'w-28'}" />
												<Skeleton class="h-3 {rowIndex % 2 === 0 ? 'w-24' : 'w-20'}" />
											</div>
										</div>
									{:else if colIndex === columns - 1}
										<!-- Last cell: Action buttons -->
										<div class="flex items-center justify-end gap-2">
											<Skeleton class="h-8 w-8 rounded-lg" />
											<Skeleton class="h-8 w-8 rounded-lg" />
										</div>
									{:else if colIndex === 1}
										<!-- Status / Badge -->
										<Skeleton class="h-6 w-20 rounded-full" />
									{:else}
										<!-- Standard data cell -->
										<Skeleton class="h-4 {colIndex % 2 === 0 ? 'w-28' : 'w-20'}" />
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</div>
