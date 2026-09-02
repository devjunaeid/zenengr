<script>
	import * as commentApi from '$lib/api/comments.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDateTime, humanize } from '$lib/utils/format.js';

	/**
	 * Comment thread for a project. Self-fetches its own data, so it can be
	 * dropped into any page that has a project id + auth token. Realm-aware:
	 * `realm="admin"` hits the tenant endpoints, `realm="client"` the client
	 * portal endpoints (used once the client project page lands).
	 *
	 * @type {{
	 *   projectId: string,
	 *   fetch: typeof fetch,
	 *   token: string,
	 *   realm?: 'admin'|'client',
	 *   staff?: boolean
	 * }}
	 */
	let { projectId, fetch: fetchFn, token, realm = 'admin', staff = true } = $props();

	/** @type {import('$lib/api/comments.js').CommentResponse[]} */
	let comments = $state([]);
	let busy = $state(true);
	/** @type {string|null} */
	let err = $state(null);
	let content = $state('');
	let isInternal = $state(false);
	let posting = $state(false);

	/** @type {string|null} */
	let editingId = $state(null);
	let editContent = $state('');
	let editBusy = $state(false);
	/** @type {string|null} */
	let deletingId = $state(null);
	let deleteBusy = $state(false);

	/**
	 * Session carries an explicit permissions list (new permission-based
	 * backend) vs the legacy role-based session where `permissions` is absent.
	 */
	const hasPermissions = $derived(Array.isArray(auth.user?.permissions));

	/**
	 * Edit/delete are staff-realm only. With permissions loaded, honour
	 * edit/comments; legacy fallback keeps admin/manager (old manage gate).
	 */
	const canEdit = $derived(
		staff &&
			(hasPermissions
				? auth.can('edit', 'comments')
				: auth.isSuperAdmin || auth.isTenantAdmin || auth.user?.role === 'manager')
	);

	/**
	 * Posting is gated server-side by post/comments. Client realm stays
	 * read+post; staff realm hides the form when the permission is missing.
	 * Legacy fallback keeps the form visible for staff as before.
	 */
	const canPost = $derived(staff ? (hasPermissions ? auth.can('post', 'comments') : true) : true);

	$effect(() => {
		void loadComments();
	});

	async function loadComments() {
		busy = true;
		err = null;
		try {
			comments = await commentApi.listComments(fetchFn, token, projectId, { realm });
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Could not load comments.';
		} finally {
			busy = false;
		}
	}

	async function submitComment() {
		if (!content.trim()) return;
		posting = true;
		err = null;
		try {
			await commentApi.postComment(
				fetchFn,
				token,
				projectId,
				{ content: content.trim(), is_internal: staff && isInternal },
				{ realm }
			);
			content = '';
			isInternal = false;
			await loadComments();
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Could not post comment.';
		} finally {
			posting = false;
		}
	}

	/**
	 * @param {import('$lib/api/comments.js').CommentResponse} c
	 */
	function startEdit(c) {
		editingId = c.id;
		editContent = c.content;
		err = null;
	}

	function cancelEdit() {
		editingId = null;
		editContent = '';
	}

	/**
	 * @param {import('$lib/api/comments.js').CommentResponse} c
	 */
	async function saveEdit(c) {
		if (!editContent.trim()) return;
		if (editContent.trim() === c.content) {
			cancelEdit();
			return;
		}
		editBusy = true;
		err = null;
		try {
			const updated = await commentApi.editComment(
				fetchFn,
				token,
				projectId,
				c.id,
				editContent.trim()
			);
			comments = comments.map((x) => (x.id === c.id ? updated : x));
			cancelEdit();
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Could not edit comment.';
		} finally {
			editBusy = false;
		}
	}

	/**
	 * @param {import('$lib/api/comments.js').CommentResponse} c
	 */
	async function confirmDelete(c) {
		deleteBusy = true;
		err = null;
		try {
			await commentApi.deleteComment(fetchFn, token, projectId, c.id);
			comments = comments.filter((x) => x.id !== c.id);
			deletingId = null;
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Could not delete comment.';
		} finally {
			deleteBusy = false;
		}
	}
</script>

{#if err}
	<p
		role="alert"
		class="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{err}
	</p>
{/if}

{#if busy}
	<div class="flex items-center gap-2 py-4 text-sm text-slate-600">
		<Spinner class="h-4 w-4 text-indigo-600" /> Loading comments…
	</div>
{:else if comments.length === 0}
	<p class="py-4 text-sm text-slate-500">No comments yet — start the conversation.</p>
{:else}
	<ul class="divide-y divide-slate-200">
		{#each comments as c (c.id)}
			<li class="py-4 first:pt-0 last:pb-0">
				<div class="flex flex-wrap items-center gap-2">
					<span class="text-sm font-medium text-slate-900">{c.author_name}</span>
					<span
						class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-500/20 ring-inset"
						>{humanize(c.author_type)}</span
					>
					{#if staff && c.is_internal}
						<span
							class="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 ring-1 ring-red-600/20 ring-inset"
							>Internal</span
						>
					{/if}
					<span class="text-xs text-slate-500">{formatDateTime(c.created_at)}</span>
					{#if canEdit && editingId !== c.id && deletingId !== c.id}
						<span class="ml-auto flex items-center gap-1">
							<button
								type="button"
								aria-label="Edit comment"
								title="Edit comment"
								onclick={() => startEdit(c)}
								class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="h-4 w-4"
									aria-hidden="true"
								>
									<path
										d="m5.433 13.917 1.262-3.155A4 4 0 0 1 7.58 9.42l6.92-6.918a2.121 2.121 0 0 1 3 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 0 1-.65-.65Z"
									/>
									<path
										d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0 0 10 3H4.75A2.75 2.75 0 0 0 2 5.75v9.5A2.75 2.75 0 0 0 4.75 18h9.5A2.75 2.75 0 0 0 17 15.25V10a.75.75 0 0 0-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5Z"
									/>
								</svg>
							</button>
							<button
								type="button"
								aria-label="Delete comment"
								title="Delete comment"
								onclick={() => {
									deletingId = c.id;
									err = null;
								}}
								class="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
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
										d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						</span>
					{/if}
				</div>
				{#if editingId === c.id}
					<textarea
						rows="3"
						maxlength="2000"
						bind:value={editContent}
						aria-label="Edit comment"
						class="mt-2 w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
					></textarea>
					<div class="mt-2 flex flex-wrap items-center gap-2">
						<button
							type="button"
							disabled={editBusy || !editContent.trim()}
							aria-busy={editBusy}
							onclick={() => saveEdit(c)}
							class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
						>
							{#if editBusy}<Spinner class="h-4 w-4 text-white" />{/if}
							Save
						</button>
						<button
							type="button"
							disabled={editBusy}
							onclick={cancelEdit}
							class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
						>
							Cancel
						</button>
					</div>
				{:else if deletingId === c.id}
					<div
						class="mt-2 flex flex-wrap items-center justify-between gap-3 rounded-md border border-red-200 bg-red-50 px-3 py-2"
						role="alertdialog"
						aria-label="Confirm delete comment"
					>
						<span class="text-sm text-red-800">Delete this comment? This cannot be undone.</span>
						<span class="flex items-center gap-2">
							<button
								type="button"
								disabled={deleteBusy}
								aria-busy={deleteBusy}
								onclick={() => confirmDelete(c)}
								class="inline-flex items-center gap-2 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
							>
								{#if deleteBusy}<Spinner class="h-4 w-4 text-white" />{/if}
								Delete
							</button>
							<button
								type="button"
								disabled={deleteBusy}
								onclick={() => {
									deletingId = null;
								}}
								class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
							>
								Cancel
							</button>
						</span>
					</div>
				{:else}
					<p class="mt-1 text-sm break-words whitespace-pre-wrap text-slate-700">{c.content}</p>
				{/if}
			</li>
		{/each}
	</ul>
{/if}

{#if canPost}
	<form
		onsubmit={(e) => {
			e.preventDefault();
			submitComment();
		}}
		class="mt-4 border-t border-slate-200 pt-4"
	>
		<label class="block">
			<span class="text-xs font-medium tracking-wide text-slate-500 uppercase">Add a comment</span>
			<textarea
				rows="3"
				maxlength="2000"
				bind:value={content}
				placeholder="Write a comment…"
				class="mt-1 w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			></textarea>
		</label>
		<div class="mt-3 flex flex-wrap items-center justify-between gap-3">
			{#if staff}
				<label class="flex items-center gap-2">
					<input
						type="checkbox"
						bind:checked={isInternal}
						class="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
					/>
					<span class="text-sm text-slate-700">Internal only</span>
				</label>
			{:else}
				<span class="text-xs text-slate-400">Shared with the client</span>
			{/if}
			<button
				type="submit"
				disabled={posting || !content.trim()}
				aria-busy={posting}
				class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if posting}<Spinner class="h-4 w-4 text-white" />{/if}
				Post comment
			</button>
		</div>
	</form>
{/if}
