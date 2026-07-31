<script>
	import { invalidateAll } from '$app/navigation';
	import { Dialog } from 'bits-ui';
	import * as adminApi from '$lib/api/admin.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);

	/** @type {'idle'|'create'|string} mode — 'create' or a plan id being edited */
	let mode = $state('idle');
	let busy = $state(false);
	/** @type {string|null} */
	let error = $state(null);

	// form fields
	let name = $state('');
	let description = $state('');
	let maxAdminUsers = $state(5);
	let maxClients = $state(50);
	let maxProjects = $state(20);
	let maxStorage = $state(512);
	let isActive = $state(true);

	function startCreate() {
		mode = 'create';
		name = '';
		description = '';
		maxAdminUsers = 5;
		maxClients = 50;
		maxProjects = 20;
		maxStorage = 512;
		isActive = true;
		error = null;
	}

	/** @param {any} plan */
	function startEdit(plan) {
		mode = plan.id;
		name = plan.name;
		description = plan.description;
		maxAdminUsers = plan.max_admin_users;
		maxClients = plan.max_clients;
		maxProjects = plan.max_active_projects;
		maxStorage = plan.max_storage_mb;
		isActive = plan.is_active;
		error = null;
	}

	function cancelForm() {
		mode = 'idle';
		error = null;
	}

	async function submit() {
		if (busy) return;
		busy = true;
		error = null;
		const limits = {
			max_admin_users: Number(maxAdminUsers),
			max_clients: Number(maxClients),
			max_active_projects: Number(maxProjects),
			max_storage_mb: Number(maxStorage)
		};
		try {
			if (mode === 'create') {
				await adminApi.createPlan(fetch, token, { name, description, ...limits });
			} else {
				await adminApi.updatePlan(fetch, token, mode, {
					name,
					description,
					...limits,
					is_active: isActive
				});
			}
			mode = 'idle';
			await invalidateAll();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			busy = false;
		}
	}

	// ---- Plan default flags ----
	/** @type {{ id: string, name: string }|null} */
	let flagPlan = $state(null);
	let flagDialogOpen = $state(false);
	let flagsLoading = $state(false);
	/** @type {Array<{ key: string, enabled: boolean }>} */
	let planFlags = $state([]);
	/** @type {string|null} */
	let flagsErr = $state(null);
	let newFlagKey = $state('');
	let newFlagEnabled = $state(true);
	let addFlagBusy = $state(false);

	async function openFlags(/** @type {{ id: string, name: string }} */ plan) {
		flagPlan = plan;
		flagDialogOpen = true;
		flagsLoading = true;
		flagsErr = null;
		planFlags = [];
		newFlagKey = '';
		newFlagEnabled = true;
		try {
			planFlags = await adminApi.listPlanFlagDefaults(fetch, token, plan.id);
		} catch (e) {
			flagsErr = e instanceof ApiError ? e.message : 'Failed to load flags.';
		} finally {
			flagsLoading = false;
		}
	}

	function closeFlags() {
		flagDialogOpen = false;
		flagPlan = null;
	}

	/** @param {string} key @param {boolean} enabled */
	async function togglePlanFlag(key, enabled) {
		if (!flagPlan) return;
		flagsErr = null;
		const prev = planFlags;
		planFlags = planFlags.map((f) => (f.key === key ? { ...f, enabled } : f));
		try {
			const updated = await adminApi.setPlanFlagDefault(fetch, token, flagPlan.id, key, enabled);
			planFlags = planFlags.map((f) => (f.key === updated.key ? updated : f));
		} catch (e) {
			planFlags = prev;
			flagsErr = e instanceof ApiError ? e.message : 'Update failed.';
		}
	}

	async function addPlanFlag() {
		if (!flagPlan) return;
		const key = newFlagKey.trim();
		if (!key || addFlagBusy) return;
		addFlagBusy = true;
		flagsErr = null;
		const prev = planFlags;
		const optimistic = { key, enabled: newFlagEnabled };
		planFlags = [...planFlags, optimistic];
		try {
			const updated = await adminApi.setPlanFlagDefault(
				fetch,
				token,
				flagPlan.id,
				key,
				newFlagEnabled
			);
			planFlags = planFlags.map((f) => (f.key === updated.key ? updated : f));
			newFlagKey = '';
		} catch (e) {
			planFlags = prev;
			flagsErr = e instanceof ApiError ? e.message : 'Add failed.';
		} finally {
			addFlagBusy = false;
		}
	}
</script>

<svelte:head><title>Plans — Super Admin</title></svelte:head>

<div class="flex items-center justify-between">
	<h1 class="text-2xl font-semibold text-slate-900">Plans</h1>
	{#if mode === 'idle'}
		<button
			type="button"
			onclick={startCreate}
			class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			New plan
		</button>
	{/if}
</div>

{#if mode !== 'idle'}
	<section
		class="mt-6 max-w-2xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		aria-labelledby="plan-form-h"
	>
		<h2 id="plan-form-h" class="text-base font-semibold text-slate-900">
			{mode === 'create' ? 'Create plan' : 'Edit plan'}
		</h2>
		{#if error}
			<p
				role="alert"
				class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{error}
			</p>
		{/if}
		<form
			class="mt-4 space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				submit();
			}}
		>
			<div>
				<label for="pl-name" class="block text-sm font-medium text-slate-700">Name</label>
				<input
					id="pl-name"
					type="text"
					bind:value={name}
					required
					maxlength="255"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="pl-desc" class="block text-sm font-medium text-slate-700">Description</label>
				<textarea
					id="pl-desc"
					bind:value={description}
					rows="2"
					maxlength="1024"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				></textarea>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="pl-users" class="block text-sm font-medium text-slate-700"
						>Max admin users</label
					>
					<input
						id="pl-users"
						type="number"
						bind:value={maxAdminUsers}
						min="1"
						required
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="pl-clients" class="block text-sm font-medium text-slate-700"
						>Max clients</label
					>
					<input
						id="pl-clients"
						type="number"
						bind:value={maxClients}
						min="1"
						required
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="pl-projects" class="block text-sm font-medium text-slate-700"
						>Max active projects</label
					>
					<input
						id="pl-projects"
						type="number"
						bind:value={maxProjects}
						min="1"
						required
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="pl-storage" class="block text-sm font-medium text-slate-700"
						>Max storage (MB)</label
					>
					<input
						id="pl-storage"
						type="number"
						bind:value={maxStorage}
						min="1"
						required
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
			{#if mode !== 'create'}
				<label class="flex items-center gap-2 text-sm text-slate-700">
					<input
						type="checkbox"
						bind:checked={isActive}
						class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
					/>
					Active (available for new tenants)
				</label>
			{/if}
			<div class="flex items-center gap-3 border-t border-slate-200 pt-4">
				<button
					type="submit"
					disabled={busy}
					aria-busy={busy}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
					{mode === 'create' ? 'Create plan' : 'Save changes'}
				</button>
				<button
					type="button"
					onclick={cancelForm}
					class="text-sm font-medium text-slate-600 hover:text-slate-500"
				>
					Cancel
				</button>
			</div>
		</form>
	</section>
{/if}

<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-200">
			<thead class="bg-slate-50">
				<tr>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Name</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Status</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Users</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Clients</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Projects</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Storage (MB)</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Tenants</th
					>
					<th
						scope="col"
						class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
						>Flags</th
					>
					<th scope="col" class="px-4 py-3"><span class="sr-only">Actions</span></th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-200">
				{#each data.plans as plan (plan.id)}
					<tr class="hover:bg-slate-50">
						<td class="px-4 py-3">
							<span class="text-sm font-medium text-slate-900">{plan.name}</span>
							{#if plan.description}
								<span class="block text-xs text-slate-500">{plan.description}</span>
							{/if}
						</td>
						<td class="px-4 py-3"
							><StatusBadge status={plan.is_active ? 'active' : 'inactive'} /></td
						>
						<td class="px-4 py-3 text-right text-sm text-slate-600">{plan.max_admin_users}</td>
						<td class="px-4 py-3 text-right text-sm text-slate-600">{plan.max_clients}</td>
						<td class="px-4 py-3 text-right text-sm text-slate-600">{plan.max_active_projects}</td>
						<td class="px-4 py-3 text-right text-sm text-slate-600">{plan.max_storage_mb}</td>
						<td class="px-4 py-3 text-right text-sm text-slate-600">{plan.tenant_count}</td>
						<td class="px-4 py-3">
							<button
								type="button"
								onclick={() => openFlags(plan)}
								class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
								aria-label={`Manage default flags for plan ${plan.name}`}
							>
								Manage flags
							</button>
						</td>
						<td class="px-4 py-3 text-right">
							<button
								type="button"
								onclick={() => startEdit(plan)}
								class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
								aria-label={`Edit plan ${plan.name}`}
							>
								Edit
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

<Dialog.Root
	bind:open={flagDialogOpen}
	onOpenChange={(o) => {
		if (!o) closeFlags();
	}}
>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 max-h-[85vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold text-slate-900">
				Default flags{flagPlan ? ` — ${flagPlan.name}` : ''}
			</Dialog.Title>
			<Dialog.Description class="mt-1 text-sm text-slate-500">
				Flags enabled here are the defaults for tenants on this plan. Per-tenant overrides take
				precedence.
			</Dialog.Description>

			{#if flagsErr}
				<p
					role="alert"
					class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{flagsErr}
				</p>
			{/if}

			<div class="mt-4">
				{#if flagsLoading}
					<div class="flex items-center gap-2 py-6 text-sm text-slate-500">
						<Spinner class="h-4 w-4" /> Loading flags…
					</div>
				{:else if planFlags.length === 0}
					<p
						class="rounded-md border border-slate-200 bg-slate-50 px-3 py-6 text-center text-sm text-slate-500"
					>
						No default flags configured for this plan yet.
					</p>
				{:else}
					<ul class="divide-y divide-slate-200 rounded-md border border-slate-200">
						{#each planFlags as flag (flag.key)}
							<li class="flex items-center justify-between gap-3 px-3 py-2.5">
								<span class="font-mono text-sm text-slate-800">{flag.key}</span>
								<div class="flex items-center gap-2">
									<button
										type="button"
										role="switch"
										aria-checked={flag.enabled}
										aria-label={`Toggle ${flag.key}`}
										onclick={() => togglePlanFlag(flag.key, !flag.enabled)}
										class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none {flag.enabled
											? 'bg-indigo-600'
											: 'bg-slate-300'}"
									>
										<span
											class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {flag.enabled
												? 'translate-x-6'
												: 'translate-x-1'}"
										></span>
									</button>
									<span class="w-7 text-xs text-slate-500">{flag.enabled ? 'On' : 'Off'}</span>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<form
				class="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-200 pt-4"
				onsubmit={(e) => {
					e.preventDefault();
					addPlanFlag();
				}}
			>
				<div class="min-w-[10rem] flex-1">
					<label for="npf-key" class="block text-xs font-medium text-slate-600">New flag key</label>
					<input
						id="npf-key"
						type="text"
						bind:value={newFlagKey}
						placeholder="feature_key"
						class="mt-1 block w-full rounded-md border-slate-300 font-mono text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<label class="flex items-center gap-2 text-sm text-slate-700">
					<input
						type="checkbox"
						bind:checked={newFlagEnabled}
						class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
					/>
					Enabled
				</label>
				<button
					type="submit"
					disabled={addFlagBusy}
					aria-busy={addFlagBusy}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if addFlagBusy}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
					Add
				</button>
			</form>

			<div class="mt-6 flex justify-end">
				<Dialog.Close
					class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					Close
				</Dialog.Close>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
