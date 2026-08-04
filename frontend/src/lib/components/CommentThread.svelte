<script>
	import * as commentApi from '$lib/api/comments.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
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
				</div>
				<p class="mt-1 text-sm whitespace-pre-wrap text-slate-700">{c.content}</p>
			</li>
		{/each}
	</ul>
{/if}

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
