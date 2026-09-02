<script>
	/**
	 * Reusable editor for an ordered list of milestone steps.
	 *
	 * The internal model uses a client-side `_key` to keep Svelte's `{#each}`
	 * happy when items are reordered or removed. Caller strips `_key` on submit.
	 *
	 * @type {{
	 *   steps: Array<{ name: string, expected_duration_days: number|null, description: string|null, _key: string }>,
	 *   readonly?: boolean
	 * }}
	 */
	let { steps = $bindable(), readonly = false } = $props();

	/** @returns {string} */
	function nextKey() {
		// Stable enough for client-side identity: timestamp + random tail.
		return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
	}

	export function addStep() {
		if (readonly) return;
		steps = [
			...steps,
			{ name: '', expected_duration_days: null, description: '', _key: nextKey() }
		];
	}

	/**
	 * @param {string} key
	 */
	export function removeStep(key) {
		if (readonly) return;
		steps = steps.filter((s) => s._key !== key);
	}

	/**
	 * @param {number} index
	 */
	export function moveStepUp(index) {
		if (readonly || index <= 0) return;
		const next = steps.slice();
		[next[index - 1], next[index]] = [next[index], next[index - 1]];
		steps = next;
	}

	/**
	 * @param {number} index
	 */
	export function moveStepDown(index) {
		if (readonly || index >= steps.length - 1) return;
		const next = steps.slice();
		[next[index], next[index + 1]] = [next[index + 1], next[index]];
		steps = next;
	}
</script>

<div class="space-y-3">
	<ol class="space-y-3" aria-label="Milestone steps">
		{#each steps as step, index (step._key)}
			<li
				class="rounded-md border border-slate-200 bg-slate-50 p-3"
				aria-label={`Step ${index + 1}`}
			>
				<div class="flex items-start gap-3">
					<div class="flex flex-col items-center gap-1 pt-1">
						<span
							class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
							aria-hidden="true"
						>
							{index + 1}
						</span>
						{#if !readonly}
							<div class="flex flex-col gap-0.5">
								<button
									type="button"
									aria-label={`Move step ${index + 1} up`}
									disabled={index === 0}
									onclick={() => moveStepUp(index)}
									class="rounded p-1 text-slate-500 hover:bg-slate-200 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="h-4 w-4"
										aria-hidden="true"
									>
										<path
											fill-rule="evenodd"
											d="M10 17a.75.75 0 01-.75-.75V5.61l-4.72 4.72a.75.75 0 11-1.06-1.06l6-6a.75.75 0 011.06 0l6 6a.75.75 0 11-1.06 1.06L10.75 5.61v10.64A.75.75 0 0110 17z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
								<button
									type="button"
									aria-label={`Move step ${index + 1} down`}
									disabled={index === steps.length - 1}
									onclick={() => moveStepDown(index)}
									class="rounded p-1 text-slate-500 hover:bg-slate-200 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="h-4 w-4"
										aria-hidden="true"
									>
										<path
											fill-rule="evenodd"
											d="M10 3a.75.75 0 01.75.75v10.64l4.72-4.72a.75.75 0 111.06 1.06l-6 6a.75.75 0 01-1.06 0l-6-6a.75.75 0 011.06-1.06l4.72 4.72V3.75A.75.75 0 0110 3z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</div>
						{/if}
					</div>
					<div class="min-w-0 flex-1 space-y-2">
						<div class="grid gap-2 sm:grid-cols-3">
							<div class="sm:col-span-2">
								<label for={`step-name-${step._key}`} class="sr-only">Step name</label>
								<input
									id={`step-name-${step._key}`}
									type="text"
									bind:value={step.name}
									required
									maxlength="255"
									placeholder="Step name"
									disabled={readonly}
									class="block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100"
								/>
							</div>
							<div>
								<label for={`step-days-${step._key}`} class="sr-only">
									Expected duration in days
								</label>
								<input
									id={`step-days-${step._key}`}
									type="number"
									min="0"
									step="1"
									bind:value={step.expected_duration_days}
									placeholder="Days"
									disabled={readonly}
									class="block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100"
								/>
							</div>
						</div>
						<div>
							<label for={`step-desc-${step._key}`} class="sr-only">Step description</label>
							<input
								id={`step-desc-${step._key}`}
								type="text"
								bind:value={step.description}
								placeholder="Optional description"
								disabled={readonly}
								class="block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100"
							/>
						</div>
					</div>
					{#if !readonly}
						<div>
							<button
								type="button"
								aria-label={`Remove step ${index + 1}`}
								onclick={() => removeStep(step._key)}
								class="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="h-5 w-5"
									aria-hidden="true"
								>
									<path
										fill-rule="evenodd"
										d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						</div>
					{/if}
				</div>
			</li>
		{/each}
	</ol>
	{#if !readonly}
		<button
			type="button"
			onclick={addStep}
			class="inline-flex items-center gap-2 rounded-md border border-dashed border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-4 w-4"
				aria-hidden="true"
			>
				<path
					d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
				/>
			</svg>
			Add step
		</button>
	{/if}
	{#if steps.length === 0 && readonly}
		<p class="text-sm text-slate-500">No steps defined.</p>
	{/if}
</div>
