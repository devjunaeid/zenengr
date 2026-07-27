<script>
	import { invalidateAll } from '$app/navigation';
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
