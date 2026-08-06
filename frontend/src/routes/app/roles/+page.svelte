<script>
	import { untrack } from 'svelte';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { Dialog } from 'bits-ui';
	import { ApiError } from '$lib/api/client.js';
	import * as rolesApi from '$lib/api/roles.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);

	/**
	 * Local copy of the roles list so mutations (create/update/delete/reset)
	 * can rewrite the UI immediately without a full reload.
	 * @type {import('$lib/api/roles.js').TenantRole[]}
	 */
	let roles = $state(untrack(() => data.roles));

	let selectedId = $state(
		untrack(() => data.roles.find((r) => r.name !== 'super_admin')?.id ?? '')
	);
	/** @type {import('$lib/api/roles.js').TenantRole|null} */
	let role = $derived(roles.find((r) => r.id === selectedId) ?? null);

	let isAdminRole = $derived(role?.name === 'admin');
	let isSuperAdminRole = $derived(role?.name === 'super_admin');
	// Admin (full access) and super_admin (global realm) are not editable.
	let canEdit = $derived(
		auth.can('manage', 'roles') && role != null && !isAdminRole && !isSuperAdminRole
	);
	// Never wipe permissions if the catalog failed to load.
	let catalogOk = $derived(data.catalog.length > 0);

	// ---- editor draft (reset whenever the selected role changes) ----
	let draftName = $state('');
	let draftDesc = $state('');
	/** @type {SvelteSet<string>} */
	let draftGranted = new SvelteSet();

	$effect(() => {
		const r = role;
		if (!r) return;
		draftName = r.name;
		draftDesc = r.description ?? '';
		draftGranted.clear();
		for (const p of r.permissions ?? []) {
			if (p.granted) draftGranted.add(`${p.action}.${p.resource}`);
		}
	});

	/**
	 * Permission catalog grouped by `group`, groups and labels sorted.
	 * @type {Array<{ group: string, items: Array<import('$lib/api/roles.js').PermissionCatalogEntry> }>}
	 */
	let groups = $derived.by(() => {
		/** @type {SvelteMap<string, Array<import('$lib/api/roles.js').PermissionCatalogEntry>>} */
		const byGroup = new SvelteMap();
		for (const c of data.catalog) {
			const g = c.group || 'Other';
			const list = byGroup.get(g) ?? [];
			list.push(c);
			byGroup.set(g, list);
		}
		const out = [];
		for (const [group, items] of byGroup) {
			items.sort((a, b) => a.label.localeCompare(b.label));
			out.push({ group, items });
		}
		out.sort((a, b) => a.group.localeCompare(b.group));
		return out;
	});

	/**
	 * @param {string} action
	 * @param {string} resource
	 */
	function togglePerm(action, resource) {
		const key = `${action}.${resource}`;
		if (draftGranted.has(key)) draftGranted.delete(key);
		else draftGranted.add(key);
	}

	// ---- save (PATCH) ----
	let saveBusy = $state(false);
	/** @type {string|null} */
	let saveErr = $state(null);
	/** @type {string|null} */
	let saveMsg = $state(null);

	async function saveRole() {
		const r = role;
		if (!r || !canEdit) return;
		saveBusy = true;
		saveErr = null;
		saveMsg = null;
		try {
			const permissions = data.catalog.map((c) => ({
				action: c.action,
				resource: c.resource,
				granted: draftGranted.has(`${c.action}.${c.resource}`)
			}));
			/** @type {any} */
			const body = { permissions };
			// System roles keep the backend-managed name/description.
			if (!r.is_system) {
				body.name = draftName.trim();
				body.description = draftDesc.trim() || null;
			}
			const updated = await rolesApi.updateRole(fetch, token, r.id, body);
			roles = roles.map((x) => (x.id === updated.id ? updated : x));
			saveMsg = 'Saved.';
		} catch (e) {
			// 422 surfaces here, e.g. "Full tenant access role cannot be edited".
			saveErr = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			saveBusy = false;
		}
	}

	// ---- reset to defaults (system manager/employee only) ----
	let resetBusy = $state(false);
	/** @type {string|null} */
	let resetErr = $state(null);

	async function resetRoleDefaults() {
		const r = role;
		if (!r || !r.is_system) return;
		resetBusy = true;
		resetErr = null;
		saveMsg = null;
		try {
			const updated = await rolesApi.resetRole(fetch, token, r.id);
			roles = roles.map((x) => (x.id === updated.id ? updated : x));
			saveMsg = 'Reset to defaults.';
		} catch (e) {
			resetErr = e instanceof ApiError ? e.message : 'Reset failed.';
		} finally {
			resetBusy = false;
		}
	}

	// ---- delete (custom roles only) ----
	let deleteOpen = $state(false);
	let deleteBusy = $state(false);
	/** @type {string|null} */
	let deleteErr = $state(null);

	async function runDelete() {
		const r = role;
		if (!r) return;
		deleteBusy = true;
		deleteErr = null;
		try {
			await rolesApi.deleteRole(fetch, token, r.id);
			deleteOpen = false;
			roles = roles.filter((x) => x.id !== r.id);
			selectedId = roles.find((x) => x.name !== 'super_admin')?.id ?? '';
			saveMsg = null;
		} catch (e) {
			// 409 (role assigned to users) surfaces the server message.
			deleteErr = e instanceof ApiError ? e.message : 'Delete failed.';
			deleteOpen = false;
		} finally {
			deleteBusy = false;
		}
	}

	// ---- new role dialog ----
	let newOpen = $state(false);
	let newBusy = $state(false);
	/** @type {string|null} */
	let newErr = $state(null);
	let newName = $state('');
	let newDesc = $state('');
	/** @type {SvelteSet<string>} */
	let newGranted = new SvelteSet();

	function openNewRole() {
		newErr = null;
		newName = '';
		newDesc = '';
		newGranted.clear();
		newOpen = true;
	}

	/**
	 * @param {string} action
	 * @param {string} resource
	 */
	function toggleNewPerm(action, resource) {
		const key = `${action}.${resource}`;
		if (newGranted.has(key)) newGranted.delete(key);
		else newGranted.add(key);
	}

	async function submitNewRole() {
		newErr = null;
		if (!newName.trim()) {
			newErr = 'Enter a role name.';
			return;
		}
		newBusy = true;
		try {
			const permissions = data.catalog.map((c) => ({
				action: c.action,
				resource: c.resource,
				granted: newGranted.has(`${c.action}.${c.resource}`)
			}));
			const created = await rolesApi.createRole(fetch, token, {
				name: newName.trim(),
				description: newDesc.trim() || null,
				permissions
			});
			newOpen = false;
			roles = [...roles, created];
			selectedId = created.id;
		} catch (e) {
			newErr = e instanceof ApiError ? e.message : 'Create failed.';
		} finally {
			newBusy = false;
		}
	}
</script>

<svelte:head><title>Roles — ZenEngr</title></svelte:head>

<div class="flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Roles</h1>
		<p class="mt-1 text-sm text-slate-500">
			Control what each team role can do. Changes apply immediately.
		</p>
	</div>
	{#if auth.can('manage', 'roles')}
		<button
			type="button"
			onclick={openNewRole}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			New role
		</button>
	{/if}
</div>

{#if deleteErr || saveErr || resetErr}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{deleteErr ?? saveErr ?? resetErr}
	</p>
{/if}
{#if saveMsg}
	<p
		role="status"
		class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
	>
		{saveMsg}
	</p>
{/if}

<div class="mt-6 grid gap-6 lg:grid-cols-[16rem_1fr]">
	<!-- Role list -->
	<section
		class="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
		aria-labelledby="roles-h"
	>
		<h2 id="roles-h" class="sr-only">Roles</h2>
		<ul class="divide-y divide-slate-200">
			{#each roles as r (r.id)}
				{@const active = r.id === selectedId}
				<li>
					<button
						type="button"
						onclick={() => (selectedId = r.id)}
						aria-pressed={active}
						class="block w-full px-4 py-3 text-left hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none {active
							? 'bg-indigo-50'
							: ''}"
					>
						<span class="flex items-center justify-between gap-2">
							<span class="text-sm font-medium text-slate-900">{r.name}</span>
							<span
								class="inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {r.is_system
									? 'bg-slate-100 text-slate-600 ring-slate-500/20'
									: 'bg-indigo-50 text-indigo-700 ring-indigo-500/20'}"
							>
								{r.is_system ? 'System' : 'Custom'}
							</span>
						</span>
						{#if r.description}
							<span class="mt-0.5 block truncate text-xs text-slate-500">{r.description}</span>
						{/if}
					</button>
				</li>
			{/each}
		</ul>
	</section>

	<!-- Editor -->
	<section class="rounded-lg border border-slate-200 bg-white shadow-sm" aria-labelledby="editor-h">
		{#if !role}
			<p class="px-6 py-10 text-sm text-slate-500">Select a role to edit.</p>
		{:else if isAdminRole}
			<div class="p-6">
				<h2 id="editor-h" class="text-base font-semibold text-slate-900">{role.name}</h2>
				<p
					role="status"
					class="mt-4 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm text-indigo-800"
				>
					Full tenant access — all permissions are always granted to this role.
				</p>
				{#if role.description}
					<p class="mt-4 text-sm text-slate-600">{role.description}</p>
				{/if}
				<p class="mt-4 text-xs text-slate-400">This role cannot be edited or deleted.</p>
			</div>
		{:else if isSuperAdminRole}
			<div class="p-6">
				<h2 id="editor-h" class="text-base font-semibold text-slate-900">{role.name}</h2>
				<p
					role="status"
					class="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600"
				>
					System role — this role exists in the global platform realm and is not editable from a
					tenant.
				</p>
			</div>
		{:else}
			<div class="p-6">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<h2 id="editor-h" class="text-base font-semibold text-slate-900">{role.name}</h2>
						<span
							class="mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {role.is_system
								? 'bg-slate-100 text-slate-600 ring-slate-500/20'
								: 'bg-indigo-50 text-indigo-700 ring-indigo-500/20'}"
						>
							{role.is_system ? 'System role' : 'Custom role'}
						</span>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						{#if role.is_system}
							<button
								type="button"
								disabled={resetBusy}
								aria-busy={resetBusy}
								onclick={resetRoleDefaults}
								class="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
							>
								{#if resetBusy}<Spinner class="h-4 w-4" />{/if}
								Reset to defaults
							</button>
						{:else}
							<button
								type="button"
								onclick={() => {
									deleteErr = null;
									deleteOpen = true;
								}}
								class="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
							>
								Delete
							</button>
						{/if}
					</div>
				</div>

				<form
					class="mt-6 space-y-4"
					onsubmit={(e) => {
						e.preventDefault();
						saveRole();
					}}
				>
					<div class="grid gap-4 sm:grid-cols-2">
						<div>
							<label for="role-name" class="block text-sm font-medium text-slate-700">Name</label>
							<input
								id="role-name"
								type="text"
								bind:value={draftName}
								disabled={role.is_system}
								class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500"
							/>
						</div>
						<div>
							<label for="role-desc" class="block text-sm font-medium text-slate-700"
								>Description</label
							>
							<input
								id="role-desc"
								type="text"
								bind:value={draftDesc}
								disabled={role.is_system}
								placeholder="What this role is for"
								class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500"
							/>
						</div>
					</div>

					{#if !catalogOk}
						<p
							role="alert"
							class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
						>
							The permission catalog could not be loaded. Save is disabled so no permissions are
							accidentally removed.
						</p>
					{:else}
						<fieldset>
							<legend class="text-sm font-medium text-slate-700">Permissions</legend>
							<div class="mt-3 space-y-4 rounded-md border border-slate-200 p-4">
								{#each groups as g (g.group)}
									<div>
										<h3 class="text-xs font-semibold tracking-wide text-slate-500 uppercase">
											{g.group}
										</h3>
										<ul class="mt-2 divide-y divide-slate-100 rounded-md border border-slate-200">
											{#each g.items as c (`${c.action}.${c.resource}`)}
												{@const key = `${c.action}.${c.resource}`}
												<li>
													<label
														class="flex cursor-pointer items-center justify-between gap-4 px-3 py-2 hover:bg-slate-50"
													>
														<span class="text-sm text-slate-700">{c.label}</span>
														<input
															type="checkbox"
															class="peer sr-only"
															checked={draftGranted.has(key)}
															onchange={() => togglePerm(c.action, c.resource)}
															aria-label={`Toggle ${c.label} for ${role.name}`}
														/>
														<span
															aria-hidden="true"
															class="relative inline-flex h-6 w-11 shrink-0 rounded-full bg-slate-300 transition-colors peer-checked:bg-indigo-600 after:absolute after:top-0.5 after:left-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:after:translate-x-5"
														></span>
													</label>
												</li>
											{/each}
										</ul>
									</div>
								{/each}
							</div>
						</fieldset>
					{/if}

					<div class="flex justify-end">
						<button
							type="submit"
							disabled={saveBusy || !canEdit || !catalogOk}
							aria-busy={saveBusy}
							class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
						>
							{#if saveBusy}<Spinner class="h-4 w-4 text-white" />{/if}
							Save
						</button>
					</div>
				</form>
			</div>
		{/if}
	</section>
</div>

<!-- New role dialog -->
<Dialog.Root bind:open={newOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">New role</Dialog.Title>
				<Dialog.Close
					type="button"
					aria-label="Close"
					class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="h-5 w-5"
						aria-hidden="true"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</Dialog.Close>
			</div>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Start with all permissions off, then grant what this role needs.
			</Dialog.Description>

			{#if newErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{newErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitNewRole();
				}}
			>
				<div>
					<label for="new-name" class="block text-sm font-medium text-slate-700">Name *</label>
					<input
						id="new-name"
						type="text"
						bind:value={newName}
						required
						placeholder="e.g. Bookkeeper"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="new-desc" class="block text-sm font-medium text-slate-700">Description</label>
					<input
						id="new-desc"
						type="text"
						bind:value={newDesc}
						placeholder="What this role is for"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				{#if catalogOk}
					<div>
						<p class="text-sm font-medium text-slate-700">Permissions</p>
						<div
							class="mt-2 max-h-64 space-y-3 overflow-y-auto rounded-md border border-slate-200 p-3"
						>
							{#each groups as g (g.group)}
								<div>
									<h3 class="text-xs font-semibold tracking-wide text-slate-500 uppercase">
										{g.group}
									</h3>
									<ul class="mt-1 divide-y divide-slate-100">
										{#each g.items as c (`${c.action}.${c.resource}`)}
											{@const key = `${c.action}.${c.resource}`}
											<li>
												<label
													class="flex cursor-pointer items-center justify-between gap-4 py-1.5"
												>
													<span class="text-sm text-slate-700">{c.label}</span>
													<input
														type="checkbox"
														class="peer sr-only"
														checked={newGranted.has(key)}
														onchange={() => toggleNewPerm(c.action, c.resource)}
														aria-label={`Grant ${c.label} to the new role`}
													/>
													<span
														aria-hidden="true"
														class="relative inline-flex h-6 w-11 shrink-0 rounded-full bg-slate-300 transition-colors peer-checked:bg-indigo-600 after:absolute after:top-0.5 after:left-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:after:translate-x-5"
													></span>
												</label>
											</li>
										{/each}
									</ul>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={newBusy}
						aria-busy={newBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if newBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Create role
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<ConfirmDialog
	bind:open={deleteOpen}
	title="Delete role"
	description={role && !role.is_system
		? `Delete the "${role.name}" role? Users assigned to it must be moved to another role first.`
		: ''}
	confirmLabel="Delete"
	destructive
	busy={deleteBusy}
	onconfirm={runDelete}
/>
