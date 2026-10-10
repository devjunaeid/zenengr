<script>
	import { untrack } from 'svelte';
	import { Dialog } from 'bits-ui';
	import { toast } from 'svelte-sonner';
	import Icon from '@iconify/svelte';
	import tagOutline from '@iconify-icons/mdi/tag-outline';
	import plus from '@iconify-icons/mdi/plus';
	import pencilOutline from '@iconify-icons/mdi/pencil-outline';
	import trashCanOutline from '@iconify-icons/mdi/trash-can-outline';
	import close from '@iconify-icons/mdi/close';
	import * as clientApi from '$lib/api/clients.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';

	let { data } = $props();

	const token = auth.token ?? '';
	const canManage = $derived(auth.can('manage', 'clients'));

	/** @type {Array<{ name: string, client_count: number }>} */
	let tags = $state(untrack(() => data.tags ?? []));
	let searchQuery = $state('');

	// Create Modal State
	let showCreateModal = $state(false);
	let createName = $state('');
	let createBusy = $state(false);
	let createErr = $state(null);

	// Edit Modal State
	let showEditModal = $state(false);
	let editOldName = $state('');
	let editNewName = $state('');
	let editClientCount = $state(0);
	let editBusy = $state(false);
	let editErr = $state(null);

	// Delete Modal State
	let showDeleteModal = $state(false);
	let deleteTargetTag = $state('');
	let deleteClientCount = $state(0);
	let deleteBusy = $state(false);

	function toSlug(name) {
		return (name || '')
			.toLowerCase()
			.trim()
			.replace(/[^\w\s-]/g, '')
			.replace(/[\s_-]+/g, '-')
			.replace(/^-+|-+$/g, '');
	}

	let filteredTags = $derived.by(() => {
		const q = searchQuery.trim().toLowerCase();
		if (!q) return tags;
		return tags.filter((t) => t.name.toLowerCase().includes(q) || toSlug(t.name).includes(q));
	});

	function openCreateModal() {
		createName = '';
		createErr = null;
		showCreateModal = true;
	}

	function openEditModal(tag) {
		editOldName = tag.name;
		editNewName = tag.name;
		editClientCount = tag.client_count;
		editErr = null;
		showEditModal = true;
	}

	function openDeleteModal(tag) {
		deleteTargetTag = tag.name;
		deleteClientCount = tag.client_count;
		showDeleteModal = true;
	}

	async function reloadTags() {
		try {
			const res = await clientApi.getTagsSummary(fetch, token);
			tags = res.items || [];
		} catch (err) {
			console.error('Failed to reload tags:', err);
		}
	}

	async function handleCreateTag() {
		const clean = createName.trim().replace(/^#+/, '');
		if (!clean) {
			createErr = 'Tag name cannot be empty.';
			return;
		}

		if (tags.some((t) => t.name.toLowerCase() === clean.toLowerCase())) {
			createErr = `Tag "${clean}" already exists.`;
			return;
		}

		createBusy = true;
		createErr = null;
		try {
			// Add locally and sort
			tags = [...tags, { name: clean, client_count: 0 }].sort((a, b) =>
				a.name.toLowerCase().localeCompare(b.name.toLowerCase())
			);
			toast.success(`Tag "${clean}" created successfully`);
			showCreateModal = false;
			createName = '';
		} catch (err) {
			createErr = err instanceof Error ? err.message : 'Failed to create tag';
		} finally {
			createBusy = false;
		}
	}

	async function handleSaveEdit() {
		const clean = editNewName.trim().replace(/^#+/, '');
		if (!clean) {
			editErr = 'Tag name cannot be empty.';
			return;
		}

		if (clean.toLowerCase() === editOldName.toLowerCase() && clean === editOldName) {
			showEditModal = false;
			return;
		}

		editBusy = true;
		editErr = null;
		try {
			const res = await clientApi.renameTag(fetch, token, editOldName, clean);
			toast.success(
				res.updated_clients > 0
					? `Renamed to "${clean}" (${res.updated_clients} client(s) updated)`
					: `Renamed to "${clean}"`
			);
			showEditModal = false;
			await reloadTags();
		} catch (err) {
			editErr = err instanceof Error ? err.message : 'Failed to rename tag';
		} finally {
			editBusy = false;
		}
	}

	async function handleDeleteTag() {
		deleteBusy = true;
		try {
			const res = await clientApi.deleteTag(fetch, token, deleteTargetTag);
			toast.success(
				res.affected_clients > 0
					? `Deleted tag "${deleteTargetTag}" from ${res.affected_clients} client(s)`
					: `Deleted tag "${deleteTargetTag}"`
			);
			showDeleteModal = false;
			await reloadTags();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Failed to delete tag');
		} finally {
			deleteBusy = false;
		}
	}
</script>

<svelte:head><title>Tags — ZenEngr</title></svelte:head>

<!-- Page Header -->
<div class="flex flex-wrap items-center justify-between gap-3">
	<div>
		<h1 class="text-2xl font-semibold text-slate-900">Tags</h1>
		<p class="mt-1 text-sm text-slate-500">
			{tags.length}
			{tags.length === 1 ? 'tag' : 'tags'} in workspace
		</p>
	</div>

	{#if canManage}
		<button
			type="button"
			onclick={openCreateModal}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			<Icon icon={plus} class="h-4 w-4" />
			<span>New tag</span>
		</button>
	{/if}
</div>

<!-- Search / Filter Bar -->
<div class="mt-6 flex flex-wrap items-end gap-3">
	<div class="min-w-0 flex-1 sm:max-w-xs">
		<label for="tag-search" class="block text-xs font-medium text-slate-600">Search tags</label>
		<input
			id="tag-search"
			type="search"
			bind:value={searchQuery}
			placeholder="Search by tag name..."
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>
</div>

<!-- Table Card (Matches clients & team modules) -->
<div class="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
	{#if tags.length === 0}
		<div class="py-12 text-center">
			<div
				class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400"
			>
				<Icon icon={tagOutline} class="h-6 w-6" />
			</div>
			<p class="mt-3 text-base font-semibold text-slate-800">No tags yet</p>
			<p class="mt-1 text-sm text-slate-500">
				Create your first tag to categorize clients and projects across your organization.
			</p>
			{#if canManage}
				<div class="mt-4">
					<button
						type="button"
						onclick={openCreateModal}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700"
					>
						<Icon icon={plus} class="h-4 w-4" />
						<span>New tag</span>
					</button>
				</div>
			{/if}
		</div>
	{:else if filteredTags.length === 0}
		<div class="py-10 text-center">
			<p class="text-sm font-medium text-slate-700">No matching tags</p>
			<p class="mt-1 text-xs text-slate-400">
				No tags matched your search "{searchQuery}".
			</p>
		</div>
	{:else}
		<!-- Desktop Table (>= lg) -->
		<div class="hidden overflow-x-auto lg:block">
			<table class="min-w-full divide-y divide-slate-200 text-left text-sm">
				<thead class="bg-slate-50 text-xs font-semibold tracking-wider text-slate-600 uppercase">
					<tr>
						<th scope="col" class="px-6 py-3.5">Tag</th>
						<th scope="col" class="px-6 py-3.5">Slug</th>
						<th scope="col" class="px-6 py-3.5 text-right">Actions</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200 bg-white">
					{#each filteredTags as tag (tag.name)}
						<tr class="transition-colors hover:bg-slate-50/80">
							<td class="px-6 py-4 whitespace-nowrap">
								<span
									class="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200"
								>
									<Icon icon={tagOutline} class="h-3.5 w-3.5 text-indigo-500" />
									{tag.name}
								</span>
							</td>

							<td class="px-6 py-4 whitespace-nowrap">
								<code
									class="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs font-medium text-slate-700"
								>
									{toSlug(tag.name)}
								</code>
							</td>

							<td class="px-6 py-4 text-right text-sm whitespace-nowrap">
								{#if canManage}
									<div class="inline-flex items-center gap-2">
										<button
											type="button"
											onclick={() => openEditModal(tag)}
											class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
										>
											<Icon icon={pencilOutline} class="h-3.5 w-3.5 text-slate-400" />
											<span>Edit</span>
										</button>
										<button
											type="button"
											onclick={() => openDeleteModal(tag)}
											class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 hover:text-red-700"
										>
											<Icon icon={trashCanOutline} class="h-3.5 w-3.5 text-red-400" />
											<span>Delete</span>
										</button>
									</div>
								{:else}
									<span class="text-xs text-slate-400">—</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Mobile / Tablet Cards (< lg) -->
		<div class="grid grid-cols-1 divide-y divide-slate-100 lg:hidden">
			{#each filteredTags as tag (tag.name)}
				<div class="flex items-center justify-between p-4">
					<div class="flex flex-wrap items-center gap-2">
						<span
							class="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200"
						>
							<Icon icon={tagOutline} class="h-3.5 w-3.5 text-indigo-500" />
							{tag.name}
						</span>
						<code
							class="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs font-medium text-slate-700"
						>
							{toSlug(tag.name)}
						</code>
					</div>

					{#if canManage}
						<div class="flex items-center gap-1">
							<button
								type="button"
								onclick={() => openEditModal(tag)}
								aria-label={`Edit ${tag.name}`}
								class="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
							>
								<Icon icon={pencilOutline} class="h-4 w-4" />
							</button>
							<button
								type="button"
								onclick={() => openDeleteModal(tag)}
								aria-label={`Delete ${tag.name}`}
								class="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
							>
								<Icon icon={trashCanOutline} class="h-4 w-4" />
							</button>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- ═════════════════════════════════════════════════════════════════════════ -->
<!-- CREATE TAG MODAL                                                          -->
<!-- ═════════════════════════════════════════════════════════════════════════ -->
<Dialog.Root bind:open={showCreateModal}>
	<Dialog.Portal to="body">
		<Dialog.Overlay class="fixed inset-0 z-[60] bg-slate-950/60 backdrop-blur-xs" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-[70] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-2xl focus:outline-none"
		>
			<div class="flex items-center justify-between border-b border-slate-100 pb-3">
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
					>
						<Icon icon={tagOutline} class="h-4 w-4" />
					</div>
					<Dialog.Title class="text-base font-semibold text-slate-900">New Tag</Dialog.Title>
				</div>
				<Dialog.Close class="rounded-lg p-1 text-slate-400 hover:bg-slate-100">
					<Icon icon={close} class="h-5 w-5" />
				</Dialog.Close>
			</div>

			<Dialog.Description class="mt-2 text-xs text-slate-500">
				Create a common tag to label and categorize clients and projects.
			</Dialog.Description>

			{#if createErr}
				<p role="alert" class="mt-3 rounded-md bg-red-50 p-2 text-xs text-red-700">{createErr}</p>
			{/if}

			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleCreateTag();
				}}
				class="mt-4 space-y-4"
			>
				<div>
					<label for="create-tag-name" class="block text-xs font-semibold text-slate-700 uppercase"
						>Tag Name *</label
					>
					<input
						id="create-tag-name"
						type="text"
						required
						bind:value={createName}
						placeholder="e.g. Corporate, VIP, Civil Engineering"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
					{#if createName.trim()}
						<p class="mt-1.5 text-xs text-slate-500">
							Slug: <code
								class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700"
								>{toSlug(createName)}</code
							>
						</p>
					{/if}
				</div>

				<div class="flex justify-end gap-2 pt-2">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={createBusy || !createName.trim()}
						class="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 disabled:opacity-60"
					>
						{#if createBusy}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
						<span>Create Tag</span>
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- ═════════════════════════════════════════════════════════════════════════ -->
<!-- EDIT TAG MODAL                                                            -->
<!-- ═════════════════════════════════════════════════════════════════════════ -->
<Dialog.Root bind:open={showEditModal}>
	<Dialog.Portal to="body">
		<Dialog.Overlay class="fixed inset-0 z-[60] bg-slate-950/60 backdrop-blur-xs" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-[70] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-2xl focus:outline-none"
		>
			<div class="flex items-center justify-between border-b border-slate-100 pb-3">
				<div class="flex items-center gap-2.5">
					<div
						class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
					>
						<Icon icon={pencilOutline} class="h-4 w-4" />
					</div>
					<Dialog.Title class="text-base font-semibold text-slate-900">Edit Tag</Dialog.Title>
				</div>
				<Dialog.Close class="rounded-lg p-1 text-slate-400 hover:bg-slate-100">
					<Icon icon={close} class="h-5 w-5" />
				</Dialog.Close>
			</div>

			<Dialog.Description class="mt-2 text-xs text-slate-500">
				Renaming will update this tag across all associated client records automatically.
			</Dialog.Description>

			{#if editErr}
				<p role="alert" class="mt-3 rounded-md bg-red-50 p-2 text-xs text-red-700">{editErr}</p>
			{/if}

			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleSaveEdit();
				}}
				class="mt-4 space-y-4"
			>
				<div>
					<label for="edit-tag-name" class="block text-xs font-semibold text-slate-700 uppercase"
						>New Tag Name *</label
					>
					<input
						id="edit-tag-name"
						type="text"
						required
						bind:value={editNewName}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
					{#if editNewName.trim()}
						<p class="mt-1.5 text-xs text-slate-500">
							Slug: <code
								class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700"
								>{toSlug(editNewName)}</code
							>
						</p>
					{/if}
				</div>

				{#if editClientCount > 0}
					<div class="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
						This will update <strong>{editClientCount}</strong> client {editClientCount === 1
							? 'record'
							: 'records'} currently tagged with "{editOldName}".
					</div>
				{/if}

				<div class="flex justify-end gap-2 pt-2">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={editBusy || !editNewName.trim()}
						class="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-indigo-700 disabled:opacity-60"
					>
						{#if editBusy}<Spinner class="h-3.5 w-3.5 text-white" />{/if}
						<span>Save Changes</span>
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- ═════════════════════════════════════════════════════════════════════════ -->
<!-- DELETE CONFIRMATION MODAL                                                 -->
<!-- ═════════════════════════════════════════════════════════════════════════ -->
<ConfirmDialog
	bind:open={showDeleteModal}
	title={`Delete tag "${deleteTargetTag}"?`}
	description={deleteClientCount > 0
		? `This tag will be permanently removed from ${deleteClientCount} client record(s). This action cannot be undone.`
		: 'This tag will be removed from the workspace. This action cannot be undone.'}
	confirmLabel="Delete tag"
	destructive={true}
	busy={deleteBusy}
	onconfirm={handleDeleteTag}
/>
