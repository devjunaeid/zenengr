<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as projectApi from '$lib/api/projects.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	const initial = untrack(() => data.project);

	let name = $state(initial.name);
	/** @type {string|null} */
	let startDate = $state(initial.start_date);
	/** @type {string|null} */
	let ownerId = $state(initial.owner_id);
	let status = $state(initial.status);
	let busy = $state(false);
	/** @type {string|null} */
	let err = $state(null);

	const statusOptions = ['draft', 'active', 'on_hold', 'completed', 'cancelled'];

	async function submit() {
		err = null;
		busy = true;
		try {
			/** @type {Record<string, any>} */
			const body = {
				name: name.trim(),
				status,
				start_date: startDate,
				owner_id: ownerId
			};
			await projectApi.updateProject(fetch, token, initial.id, body);
			goto(resolve('/app/projects/[id]', { id: initial.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Edit {initial.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/projects')} class="hover:text-indigo-600">Projects</a>
		</li>
		<li aria-hidden="true">/</li>
		<li>
			<a href={resolve('/app/projects/[id]', { id: initial.id })} class="hover:text-indigo-600"
				>{initial.name}</a
			>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">Edit</li>
	</ol>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">Edit project</h1>
<p class="mt-1 text-sm text-slate-500">
	Services are added or removed from the project detail page.
</p>

{#if err}
	<p
		role="alert"
		class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{err}
	</p>
{/if}

<form
	class="mt-6 max-w-2xl space-y-5"
	onsubmit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<div>
		<label for="p-name" class="block text-sm font-medium text-slate-700">Name *</label>
		<input
			id="p-name"
			type="text"
			bind:value={name}
			required
			maxlength="255"
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>

	<div class="grid gap-4 sm:grid-cols-2">
		<div>
			<label for="p-start" class="block text-sm font-medium text-slate-700">Start date</label>
			<input
				id="p-start"
				type="date"
				bind:value={startDate}
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>
		<div>
			<label for="p-status" class="block text-sm font-medium text-slate-700">Status</label>
			<select
				id="p-status"
				bind:value={status}
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			>
				{#each statusOptions as opt (opt)}
					<option value={opt}>{humanize(opt)}</option>
				{/each}
			</select>
		</div>
	</div>

	<div>
		<label for="p-owner" class="block text-sm font-medium text-slate-700">Owner</label>
		<select
			id="p-owner"
			bind:value={ownerId}
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		>
			<option value={null}>— Unassigned —</option>
			{#each data.users as u (u.id)}
				<option value={u.id}>{u.full_name} ({u.email})</option>
			{/each}
		</select>
	</div>

	<div class="flex items-center gap-3 pt-2">
		<button
			type="submit"
			disabled={busy}
			aria-busy={busy}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
			Save changes
		</button>
		<a
			href={resolve('/app/projects/[id]', { id: initial.id })}
			class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Cancel
		</a>
	</div>
</form>
