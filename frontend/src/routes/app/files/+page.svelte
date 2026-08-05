<script>
	import { untrack } from 'svelte';
	import { SvelteSet, SvelteURLSearchParams } from 'svelte/reactivity';
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { Dialog } from 'bits-ui';
	import { ApiError } from '$lib/api/client.js';
	import * as filesApi from '$lib/api/files.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { fmtBytes, formatDateTime } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);

	let canManage = $derived(auth.user?.role === 'admin' || auth.user?.role === 'manager');

	// ---- current location (folder/scope/project), mirrors URL params ----
	let folderId = $state(untrack(() => data.filters.folder_id));
	let scope = $state(untrack(() => data.filters.scope));
	let projectId = $state(untrack(() => data.filters.project_id));
	let q = $state(untrack(() => data.filters.q));

	let uploadAllowed = $derived(scope === 'user' || canManage);

	/** @type {string|null} */
	let actionErr = $state(null);

	// ---- tree helpers ----
	/**
	 * @typedef {import('$lib/api/files.js').FolderTreeNode} FolderTreeNode
	 */

	/**
	 * Normalize the server tree: guarantee the three scope roots exist.
	 * @type {FolderTreeNode[]}
	 */
	let treeRoots = $derived.by(() => {
		const roots = Array.isArray(data.folders) ? data.folders : [];
		/** @type {FolderTreeNode} */
		const my = roots.find((r) => r.scope === 'user') ?? {
			id: null,
			name: 'My files',
			scope: 'user',
			project_id: null,
			children: []
		};
		/** @type {FolderTreeNode} */
		const team = roots.find((r) => r.scope === 'tenant') ?? {
			id: null,
			name: 'Team files',
			scope: 'tenant',
			project_id: null,
			children: []
		};
		/** @type {FolderTreeNode} */
		const proj = roots.find((r) => r.scope === 'project') ?? {
			id: null,
			name: 'Project files',
			scope: 'project',
			project_id: null,
			children: []
		};
		return [my, team, proj];
	});

	/** Collapsed node keys; empty = everything expanded */
	let collapsed = new SvelteSet(/** @type {string[]} */ ([]));

	/**
	 * @param {FolderTreeNode} node
	 */
	function nodeKey(node) {
		return node.id ?? `root:${node.scope}`;
	}

	/**
	 * @param {FolderTreeNode} node
	 */
	function isScopeRoot(node) {
		return treeRoots.some((r) => r === node);
	}

	/**
	 * @param {string} key
	 */
	function toggleExpand(key) {
		if (collapsed.has(key)) {
			collapsed.delete(key);
		} else {
			collapsed.add(key);
		}
	}

	/**
	 * @param {FolderTreeNode} node
	 */
	function isActiveNode(node) {
		if (isScopeRoot(node)) {
			return (
				node.scope === scope &&
				folderId === '' &&
				(node.scope !== 'project' || String(node.project_id ?? '') === String(projectId ?? ''))
			);
		}
		return node.scope === scope && String(node.id ?? '') === String(folderId ?? '');
	}

	/**
	 * @param {FolderTreeNode} node
	 */
	function selectNode(node) {
		scope = node.scope;
		projectId = node.scope === 'project' ? (node.project_id ?? '') : '';
		folderId = isScopeRoot(node) ? '' : (node.id ?? '');
		applyUrl(1);
	}

	/**
	 * Find the active folder node and its ancestor path (roots included).
	 * @param {FolderTreeNode[]} nodes
	 * @param {FolderTreeNode[]} ancestors
	 * @returns {FolderTreeNode[]|null}
	 */
	function findNodePath(nodes, ancestors) {
		for (const node of nodes) {
			if (isActiveNode(node)) return [...ancestors, node];
			const found = findNodePath(node.children, [...ancestors, node]);
			if (found) return found;
		}
		return null;
	}

	/**
	 * All folders under a scope root, depth-first.
	 * @param {FolderTreeNode} root
	 * @param {FolderTreeNode[]} [out]
	 */
	function flattenByScope(root, out = []) {
		for (const child of root.children) {
			out.push(child);
			flattenByScope(child, out);
		}
		return out;
	}

	let tenantFolders = $derived(flattenByScope(treeRoots[1]));

	/**
	 * Project-scope folders for one project (the per-project folder + nested).
	 * @param {string} pid
	 */
	function projectFoldersFor(pid) {
		const projRoot = treeRoots[2];
		const out = [];
		for (const child of projRoot.children) {
			if (child.project_id === pid) {
				out.push(child);
				flattenByScope(child, out);
			}
		}
		return out;
	}

	/**
	 * @param {string|null|undefined} pid
	 */
	function projectName(pid) {
		return data.projects.find((p) => p.id === pid)?.name;
	}

	// ---- breadcrumb ----
	/** @type {Array<{ label: string, node: FolderTreeNode|null }>} */
	let breadcrumb = $derived.by(() => {
		if (scope === 'user') {
			return [{ label: 'My files', node: treeRoots[0] }];
		}
		const rootLabel = scope === 'tenant' ? 'Team files' : 'Project files';
		const rootNode = scope === 'tenant' ? treeRoots[1] : treeRoots[2];
		const segs = [{ label: rootLabel, node: rootNode }];
		const path = findNodePath(data.folders, []);
		for (const n of path ?? []) {
			if (isScopeRoot(n)) continue;
			segs.push({ label: n.name, node: n });
		}
		return segs;
	});

	// ---- navigation ----
	/**
	 * @param {number} p
	 */
	function buildUrl(p) {
		const params = new SvelteURLSearchParams();
		if (folderId) params.set('folder_id', folderId);
		if (scope !== 'user') params.set('scope', scope);
		if (projectId) params.set('project_id', projectId);
		if (q.trim()) params.set('q', q.trim());
		if (p > 1) params.set('page', String(p));
		const qs = params.toString();
		return qs ? `${resolve('/app/files')}?${qs}` : resolve('/app/files');
	}

	/**
	 * @param {number} p
	 */
	function applyUrl(p) {
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- query string appended to a resolved route
		goto(buildUrl(p));
	}

	/** @type {ReturnType<typeof setTimeout>|undefined} */
	let qTimer;
	function onQInput() {
		clearTimeout(qTimer);
		qTimer = setTimeout(() => applyUrl(1), 400);
	}

	// ---- upload dialog ----
	let uploadOpen = $state(false);
	let uploadBusy = $state(false);
	/** @type {string|null} */
	let uploadErr = $state(null);
	/** @type {File|null} */
	let uploadFileSel = $state(null);
	/** @type {'user'|'tenant'|'project'} */
	let uploadScope = $state(/** @type {'user'|'tenant'|'project'} */ ('user'));
	let uploadFolderId = $state('');
	let uploadProjectId = $state('');

	let uploadFolderOptions = $derived(
		uploadScope === 'tenant'
			? tenantFolders
			: uploadScope === 'project' && uploadProjectId
				? projectFoldersFor(uploadProjectId)
				: []
	);

	function openUpload() {
		uploadErr = null;
		uploadFileSel = null;
		uploadScope = /** @type {'user'|'tenant'|'project'} */ (scope);
		uploadFolderId = folderId;
		uploadProjectId = projectId;
		uploadOpen = true;
	}

	async function submitUpload() {
		uploadErr = null;
		if (!uploadFileSel) {
			uploadErr = 'Pick a file to upload.';
			return;
		}
		if (uploadScope === 'project' && !uploadProjectId) {
			uploadErr = 'Pick a project.';
			return;
		}
		const fd = new FormData();
		fd.append('file', uploadFileSel);
		fd.append('scope', uploadScope);
		if (uploadScope !== 'user' && uploadFolderId) fd.append('folder_id', uploadFolderId);
		if (uploadScope === 'project') fd.append('project_id', uploadProjectId);
		uploadBusy = true;
		try {
			await filesApi.uploadFile(fetch, token, fd);
			uploadOpen = false;
			await invalidateAll();
		} catch (e) {
			uploadErr = e instanceof ApiError ? e.message : 'Upload failed.';
		} finally {
			uploadBusy = false;
		}
	}

	// ---- new folder dialog ----
	let folderOpen = $state(false);
	let folderBusy = $state(false);
	/** @type {string|null} */
	let folderErr = $state(null);
	let folderName = $state('');
	let folderProjectId = $state('');

	function openNewFolder() {
		folderErr = null;
		folderName = '';
		folderProjectId = projectId;
		folderOpen = true;
	}

	async function submitNewFolder() {
		folderErr = null;
		if (!folderName.trim()) {
			folderErr = 'Enter a folder name.';
			return;
		}
		if (scope === 'project' && !folderProjectId) {
			folderErr = 'Pick a project.';
			return;
		}
		folderBusy = true;
		try {
			/** @type {Record<string, any>} */
			const body = { name: folderName.trim(), scope };
			if (folderId) body.parent_id = folderId;
			if (scope === 'project') body.project_id = folderProjectId;
			await filesApi.createFolder(fetch, token, /** @type {any} */ (body));
			folderOpen = false;
			await invalidateAll();
		} catch (e) {
			folderErr = e instanceof ApiError ? e.message : 'Could not create folder.';
		} finally {
			folderBusy = false;
		}
	}

	// ---- file actions ----
	/**
	 * @param {import('$lib/api/files.js').FileAssetItem} file
	 */
	function canActOnFile(file) {
		if (file.scope === 'user') return file.created_by_id === auth.user?.id;
		return canManage;
	}

	/**
	 * @param {import('$lib/api/files.js').FileAssetItem} file
	 */
	async function runDownload(file) {
		actionErr = null;
		try {
			await filesApi.downloadFile(fetch, token, file.id, file.name);
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Download failed.';
		}
	}

	// rename
	let renameOpen = $state(false);
	let renameBusy = $state(false);
	/** @type {string|null} */
	let renameErr = $state(null);
	let renameName = $state('');
	/** @type {import('$lib/api/files.js').FileAssetItem|null} */
	let renameTarget = $state(/** @type {import('$lib/api/files.js').FileAssetItem|null} */ (null));

	/**
	 * @param {import('$lib/api/files.js').FileAssetItem} file
	 */
	function openRename(file) {
		renameTarget = file;
		renameName = file.name;
		renameErr = null;
		renameOpen = true;
	}

	async function submitRename() {
		if (!renameTarget) return;
		renameErr = null;
		if (!renameName.trim()) {
			renameErr = 'Enter a name.';
			return;
		}
		renameBusy = true;
		try {
			await filesApi.renameFile(fetch, token, renameTarget.id, { name: renameName.trim() });
			renameOpen = false;
			await invalidateAll();
		} catch (e) {
			renameErr = e instanceof ApiError ? e.message : 'Rename failed.';
		} finally {
			renameBusy = false;
		}
	}

	// move
	let moveOpen = $state(false);
	let moveBusy = $state(false);
	/** @type {string|null} */
	let moveErr = $state(null);
	let moveFolderId = $state('');
	/** @type {import('$lib/api/files.js').FileAssetItem|null} */
	let moveTarget = $state(/** @type {import('$lib/api/files.js').FileAssetItem|null} */ (null));

	let moveFolderOptions = $derived(
		moveTarget
			? moveTarget.scope === 'user'
				? []
				: moveTarget.scope === 'tenant'
					? tenantFolders
					: projectFoldersFor(moveTarget.project_id ?? '')
			: []
	);

	let moveRootLabel = $derived(
		moveTarget
			? moveTarget.scope === 'user'
				? 'My files'
				: moveTarget.scope === 'tenant'
					? 'Team files'
					: (projectName(moveTarget.project_id) ?? 'Project files')
			: ''
	);

	/**
	 * @param {import('$lib/api/files.js').FileAssetItem} file
	 */
	function openMove(file) {
		moveTarget = file;
		moveFolderId = file.folder_id ?? '';
		moveErr = null;
		moveOpen = true;
	}

	async function submitMove() {
		if (!moveTarget) return;
		moveErr = null;
		moveBusy = true;
		try {
			await filesApi.moveFile(fetch, token, moveTarget.id, { folder_id: moveFolderId || null });
			moveOpen = false;
			await invalidateAll();
		} catch (e) {
			moveErr = e instanceof ApiError ? e.message : 'Move failed.';
		} finally {
			moveBusy = false;
		}
	}

	// delete
	let deleteOpen = $state(false);
	let deleteBusy = $state(false);
	/** @type {import('$lib/api/files.js').FileAssetItem|null} */
	let deleteTarget = $state(/** @type {import('$lib/api/files.js').FileAssetItem|null} */ (null));

	/**
	 * @param {import('$lib/api/files.js').FileAssetItem} file
	 */
	function openDelete(file) {
		deleteTarget = file;
		deleteOpen = true;
	}

	async function runDelete() {
		if (!deleteTarget) return;
		deleteBusy = true;
		actionErr = null;
		try {
			await filesApi.deleteFile(fetch, token, deleteTarget.id);
			deleteTarget = null;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Could not delete file.';
		} finally {
			deleteBusy = false;
		}
	}

	// ---- display helpers ----
	/**
	 * @typedef {object} FlatNode
	 * @property {FolderTreeNode} node
	 * @property {number} depth
	 * @property {boolean} hasKids
	 * @property {string} key
	 */

	/** @type {FlatNode[]} */
	let flatNodes = $derived.by(() => {
		/** @type {FlatNode[]} */
		const out = [];
		/**
		 * @param {FolderTreeNode} n
		 * @param {number} depth
		 */
		const walk = (n, depth) => {
			const key = nodeKey(n);
			const hasKids = n.children.length > 0;
			out.push({ node: n, depth, hasKids, key });
			if (hasKids && !collapsed.has(key)) {
				for (const c of n.children) walk(c, depth + 1);
			}
		};
		for (const root of treeRoots) walk(root, 0);
		return out;
	});

	/**
	 * @param {string|null|undefined} scopeValue
	 */
	function scopeLabel(scopeValue) {
		return scopeValue === 'user' ? 'My' : scopeValue === 'tenant' ? 'Team' : 'Project';
	}

	/**
	 * @param {string|null|undefined} scopeValue
	 */
	function scopePillClass(scopeValue) {
		return scopeValue === 'user'
			? 'bg-slate-100 text-slate-600 ring-slate-500/20'
			: scopeValue === 'tenant'
				? 'bg-indigo-50 text-indigo-700 ring-indigo-500/20'
				: 'bg-amber-50 text-amber-800 ring-amber-500/20';
	}

	/**
	 * @param {string|null|undefined} contentType
	 */
	function fileKind(contentType) {
		const t = (contentType ?? '').toLowerCase();
		if (t.startsWith('image/')) return 'image';
		if (t === 'application/pdf') return 'pdf';
		if (t.startsWith('text/')) return 'text';
		return 'file';
	}

	const actionBtn =
		'rounded px-2 py-1 text-sm font-medium hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40';
</script>

<svelte:head><title>Files — ZenEngr</title></svelte:head>

<div class="grid gap-6 lg:grid-cols-4">
	<aside class="lg:col-span-1">
		<div class="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
			<p class="px-2 pb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">Folders</p>
			<nav aria-label="Files" class="space-y-0.5">
				{#each flatNodes as row (row.key)}
					{@const node = row.node}
					{@const active = isActiveNode(node)}
					<div class="flex items-center gap-0.5" style="padding-left: {row.depth * 0.75}rem">
						<button
							type="button"
							aria-label={row.hasKids
								? collapsed.has(row.key)
									? `Expand ${node.name}`
									: `Collapse ${node.name}`
								: undefined}
							onclick={() => row.hasKids && toggleExpand(row.key)}
							class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-slate-400 hover:bg-slate-100 hover:text-slate-600 {row.hasKids
								? ''
								: 'invisible'}"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="h-3.5 w-3.5 transition-transform {collapsed.has(row.key) ? '' : 'rotate-90'}"
								aria-hidden="true"
							>
								<path
									fill-rule="evenodd"
									d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							type="button"
							onclick={() => selectNode(node)}
							class="min-w-0 flex-1 rounded-md px-2 py-1 text-left text-sm {active
								? 'bg-indigo-50 font-medium text-indigo-700'
								: 'text-slate-700 hover:bg-slate-100'}"
						>
							<span class="block truncate">{node.name}</span>
						</button>
					</div>
				{/each}
			</nav>
		</div>
	</aside>

	<div class="min-w-0 lg:col-span-3">
		<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
			<ol class="flex flex-wrap items-center gap-1">
				{#each breadcrumb as seg, i (seg.label + i)}
					{#if i > 0}<li aria-hidden="true">/</li>{/if}
					<li>
						{#if i < breadcrumb.length - 1 && seg.node}
							<button
								type="button"
								onclick={() => selectNode(/** @type {FolderTreeNode} */ (seg.node))}
								class="hover:text-indigo-600"
							>
								{seg.label}
							</button>
						{:else}
							<span class="font-medium text-slate-700">{seg.label}</span>
						{/if}
					</li>
				{/each}
			</ol>
		</nav>

		<div class="mt-3 flex flex-wrap items-center justify-between gap-3">
			<div class="flex flex-wrap items-center gap-2">
				<button
					type="button"
					disabled={!uploadAllowed}
					title={uploadAllowed ? undefined : 'Admins and managers upload team and project files.'}
					onclick={openUpload}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					Upload
				</button>
				{#if scope !== 'user'}
					<button
						type="button"
						disabled={!canManage}
						title={canManage
							? undefined
							: 'Only admins and managers create team or project folders.'}
						onclick={openNewFolder}
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						New folder
					</button>
				{/if}
			</div>
			<form
				role="search"
				onsubmit={(e) => {
					e.preventDefault();
					clearTimeout(qTimer);
					applyUrl(1);
				}}
			>
				<label for="files-q" class="sr-only">Search files</label>
				<input
					id="files-q"
					type="search"
					placeholder="Search files…"
					bind:value={q}
					oninput={onQInput}
					class="block w-64 rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</form>
		</div>

		{#if actionErr}
			<p
				role="alert"
				class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{actionErr}
			</p>
		{/if}

		<section
			class="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
			aria-labelledby="files-h"
		>
			<div class="flex items-center justify-between border-b border-slate-200 px-6 py-4">
				<div>
					<h2 id="files-h" class="text-base font-semibold text-slate-900">Files</h2>
					<p class="mt-0.5 text-sm text-slate-500">
						{data.files.total}
						{data.files.total === 1 ? 'file' : 'files'}
					</p>
				</div>
			</div>
			{#if data.files.items.length === 0}
				{#if q.trim()}
					<p class="px-6 py-8 text-sm text-slate-500">No files match "{q}".</p>
				{:else}
					<EmptyState
						title="No files yet"
						description="Upload a file to share it with your team or a project."
					>
						{#if uploadAllowed}
							<button
								type="button"
								onclick={openUpload}
								class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
							>
								Upload a file
							</button>
						{/if}
					</EmptyState>
				{/if}
			{:else}
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
									>Size</th
								>
								<th
									scope="col"
									class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Type</th
								>
								<th
									scope="col"
									class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Scope</th
								>
								<th
									scope="col"
									class="px-4 py-3 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Uploaded</th
								>
								<th
									scope="col"
									class="px-4 py-3 text-right text-xs font-semibold tracking-wide text-slate-600 uppercase"
									>Actions</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-200">
							{#each data.files.items as file (file.id)}
								{@const canAct = canActOnFile(file)}
								<tr class="hover:bg-slate-50">
									<td class="max-w-xs px-4 py-3">
										<div class="flex items-center gap-2">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="h-4 w-4 shrink-0 text-slate-400"
												aria-hidden="true"
											>
												{#if fileKind(file.content_type) === 'image'}
													<path
														fill-rule="evenodd"
														d="M1 5.25A2.25 2.25 0 013.25 3h13.5A2.25 2.25 0 0119 5.25v9.5A2.25 2.25 0 0116.75 17H3.25A2.25 2.25 0 011 14.75v-9.5zm1.5 5.81v3.69c0 .414.336.75.75.75h13.5a.75.75 0 00.75-.75v-2.69l-2.22-2.219a.75.75 0 00-1.06 0l-1.91 1.91-3.22-3.22a.75.75 0 00-1.06 0L2.5 11.06zm8.5-4.31a1 1 0 112 0 1 1 0 01-2 0z"
														clip-rule="evenodd"
													/>
												{:else}
													<path
														fill-rule="evenodd"
														d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.414a1.5 1.5 0 00-.44-1.06l-3.914-3.914A1.5 1.5 0 0011.586 2H4.5zM6 5.5a.75.75 0 01.75-.75h4.5a.75.75 0 010 1.5h-4.5A.75.75 0 016 5.5zM6.75 9a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zM6 12.25a.75.75 0 01.75-.75h4.5a.75.75 0 010 1.5h-4.5a.75.75 0 01-.75-.75z"
														clip-rule="evenodd"
													/>
												{/if}
											</svg>
											<span class="truncate text-sm font-medium text-slate-900" title={file.name}>
												{file.name}
											</span>
										</div>
									</td>
									<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-700"
										>{fmtBytes(file.size_bytes)}</td
									>
									<td class="max-w-[10rem] px-4 py-3">
										<span class="block truncate text-sm text-slate-600" title={file.content_type}>
											{file.content_type}
										</span>
									</td>
									<td class="px-4 py-3">
										<span
											class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset {scopePillClass(
												file.scope
											)}"
										>
											{scopeLabel(file.scope)}
										</span>
									</td>
									<td class="px-4 py-3 text-sm whitespace-nowrap text-slate-600"
										>{formatDateTime(file.created_at)}</td
									>
									<td class="px-4 py-3">
										<div class="flex items-center justify-end gap-1">
											<button
												type="button"
												onclick={() => runDownload(file)}
												class="{actionBtn} text-indigo-600 hover:text-indigo-700"
											>
												Download
											</button>
											<button
												type="button"
												disabled={!canAct}
												title={canAct ? undefined : 'Not permitted at this scope.'}
												onclick={() => openRename(file)}
												class="{actionBtn} text-slate-600 hover:text-slate-900"
											>
												Rename
											</button>
											<button
												type="button"
												disabled={!canAct}
												title={canAct ? undefined : 'Not permitted at this scope.'}
												onclick={() => openMove(file)}
												class="{actionBtn} text-slate-600 hover:text-slate-900"
											>
												Move
											</button>
											<button
												type="button"
												disabled={!canAct}
												title={canAct ? undefined : 'Not permitted at this scope.'}
												onclick={() => openDelete(file)}
												class="{actionBtn} text-red-600 hover:text-red-700"
											>
												Delete
											</button>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				<Pagination
					page={data.files.page}
					pageSize={data.files.page_size}
					total={data.files.total}
					onpage={applyUrl}
				/>
			{/if}
		</section>
	</div>
</div>

<!-- Upload dialog (bits-ui Dialog) -->
<Dialog.Root bind:open={uploadOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<div class="flex items-center justify-between">
				<Dialog.Title class="text-lg font-semibold text-slate-900">Upload file</Dialog.Title>
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
				Pick a file and where it should live. Per-file limit is 25 MB.
			</Dialog.Description>

			{#if uploadErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{uploadErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitUpload();
				}}
			>
				<div>
					<label for="up-file" class="block text-sm font-medium text-slate-700">File *</label>
					<input
						id="up-file"
						type="file"
						onchange={(e) =>
							(uploadFileSel =
								/** @type {HTMLInputElement} */ (e.currentTarget).files?.[0] ?? null)}
						class="mt-1 block w-full text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
					/>
				</div>

				<fieldset>
					<legend class="text-sm font-medium text-slate-700">Scope *</legend>
					<div class="mt-2 flex flex-wrap gap-4">
						<label class="flex items-center gap-2 text-sm text-slate-700">
							<input
								type="radio"
								name="up-scope"
								value="user"
								bind:group={uploadScope}
								class="text-indigo-600 focus:ring-indigo-500"
							/>
							My files
						</label>
						<label class="flex items-center gap-2 text-sm text-slate-700">
							<input
								type="radio"
								name="up-scope"
								value="tenant"
								bind:group={uploadScope}
								class="text-indigo-600 focus:ring-indigo-500"
							/>
							Team files
						</label>
						<label class="flex items-center gap-2 text-sm text-slate-700">
							<input
								type="radio"
								name="up-scope"
								value="project"
								bind:group={uploadScope}
								class="text-indigo-600 focus:ring-indigo-500"
							/>
							Project files
						</label>
					</div>
				</fieldset>

				{#if uploadScope === 'project'}
					<div>
						<label for="up-project" class="block text-sm font-medium text-slate-700"
							>Project *</label
						>
						<select
							id="up-project"
							bind:value={uploadProjectId}
							required
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						>
							<option value="" disabled>Select a project</option>
							{#each data.projects as p (p.id)}
								<option value={p.id}>{p.name}</option>
							{/each}
						</select>
					</div>
				{/if}
				{#if uploadScope === 'tenant' || uploadScope === 'project'}
					<div>
						<label for="up-folder" class="block text-sm font-medium text-slate-700">Folder</label>
						<select
							id="up-folder"
							bind:value={uploadFolderId}
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						>
							<option value="">
								{uploadScope === 'tenant' ? 'Team files (root)' : 'Project files (root)'}
							</option>
							{#each uploadFolderOptions as f (f.id)}
								<option value={f.id}>{f.name}</option>
							{/each}
						</select>
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
						disabled={uploadBusy}
						aria-busy={uploadBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if uploadBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Upload
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- New folder dialog -->
<Dialog.Root bind:open={folderOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold text-slate-900">New folder</Dialog.Title>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Create a subfolder inside
				{breadcrumb.length > 0 ? breadcrumb[breadcrumb.length - 1].label : 'this location'}.
			</Dialog.Description>

			{#if folderErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{folderErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitNewFolder();
				}}
			>
				<div>
					<label for="nf-name" class="block text-sm font-medium text-slate-700">Name *</label>
					<input
						id="nf-name"
						type="text"
						bind:value={folderName}
						required
						placeholder="e.g. Contracts"
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				{#if scope === 'project'}
					<div>
						<label for="nf-project" class="block text-sm font-medium text-slate-700"
							>Project *</label
						>
						<select
							id="nf-project"
							bind:value={folderProjectId}
							required
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						>
							<option value="" disabled>Select a project</option>
							{#each data.projects as p (p.id)}
								<option value={p.id}>{p.name}</option>
							{/each}
						</select>
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
						disabled={folderBusy}
						aria-busy={folderBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if folderBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Create folder
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Rename file dialog -->
<Dialog.Root bind:open={renameOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold text-slate-900">Rename file</Dialog.Title>

			{#if renameErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{renameErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitRename();
				}}
			>
				<div>
					<label for="rn-name" class="block text-sm font-medium text-slate-700">Name *</label>
					<input
						id="rn-name"
						type="text"
						bind:value={renameName}
						required
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={renameBusy}
						aria-busy={renameBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if renameBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Rename
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<!-- Move file dialog -->
<Dialog.Root bind:open={moveOpen}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50" />
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-xl focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold text-slate-900">Move file</Dialog.Title>
			<Dialog.Description class="mt-2 text-sm text-slate-600">
				Move {moveTarget?.name ?? 'this file'} to another folder.
			</Dialog.Description>

			{#if moveErr}
				<p
					role="alert"
					class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					{moveErr}
				</p>
			{/if}

			<form
				class="mt-4 space-y-4"
				onsubmit={(e) => {
					e.preventDefault();
					submitMove();
				}}
			>
				<div>
					<label for="mv-folder" class="block text-sm font-medium text-slate-700">Folder</label>
					<select
						id="mv-folder"
						bind:value={moveFolderId}
						class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					>
						<option value="">{moveRootLabel}</option>
						{#each moveFolderOptions as f (f.id)}
							<option value={f.id}>{f.name}</option>
						{/each}
					</select>
				</div>

				<div class="mt-6 flex justify-end gap-3">
					<Dialog.Close
						type="button"
						class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
					>
						Cancel
					</Dialog.Close>
					<button
						type="submit"
						disabled={moveBusy}
						aria-busy={moveBusy}
						class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if moveBusy}<Spinner class="h-4 w-4 text-white" />{/if}
						Move
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<ConfirmDialog
	bind:open={deleteOpen}
	title="Delete file"
	description={deleteTarget
		? `Permanently delete "${deleteTarget.name}"? This cannot be undone.`
		: ''}
	confirmLabel="Delete"
	destructive
	busy={deleteBusy}
	onconfirm={runDelete}
/>
