<script>
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as serviceApi from '$lib/api/services.js';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { formatDateTime, fmtPrice } from '$lib/utils/format.js';

	let { data } = $props();

	const token = /** @type {string} */ (auth.token);
	let canManage = $derived(auth.can('manage', 'services'));
	let isEmployee = $derived(auth.user?.role === 'employee');

	/** @type {null | 'activate' | 'deactivate'} */
	let toggleAction = $state(null);
	let toggleBusy = $state(false);
	let deleteOpen = $state(false);
	let deleteBusy = $state(false);
	/** @type {string|null} */
	let actionErr = $state(null);

	async function runToggle() {
		if (!toggleAction) return;
		toggleBusy = true;
		actionErr = null;
		try {
			await serviceApi.updateService(fetch, token, data.service.id, {
				is_active: toggleAction === 'activate'
			});
			toggleAction = null;
			await invalidateAll();
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Action failed.';
		} finally {
			toggleBusy = false;
		}
	}

	async function runDelete() {
		deleteBusy = true;
		actionErr = null;
		try {
			await serviceApi.deleteService(fetch, token, data.service.id);
			goto(resolve('/app/services'));
		} catch (e) {
			actionErr = e instanceof ApiError ? e.message : 'Delete failed.';
			deleteOpen = false;
			deleteBusy = false;
		}
	}
</script>

<svelte:head><title>{data.service.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/services')} class="hover:text-indigo-600">Services</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">{data.service.name}</li>
	</ol>
</nav>

<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
	<div class="flex items-center gap-3">
		<h1 class="text-2xl font-semibold text-slate-900">{data.service.name}</h1>
		<StatusBadge status={data.service.is_active ? 'active' : 'inactive'} />
	</div>
	{#if canManage}
		<div class="flex items-center gap-2">
			<a
				href={resolve('/app/services/[id]/edit', { id: data.service.id })}
				class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
			>
				Edit
			</a>
			{#if data.service.is_active}
				<button
					type="button"
					onclick={() => (toggleAction = 'deactivate')}
					class="rounded-md border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium text-amber-800 hover:bg-amber-50 focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:outline-none"
				>
					Deactivate
				</button>
			{:else}
				<button
					type="button"
					onclick={() => (toggleAction = 'activate')}
					class="rounded-md border border-green-300 bg-white px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-50 focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:outline-none"
				>
					Activate
				</button>
			{/if}
			<button
				type="button"
				onclick={() => (deleteOpen = true)}
				class="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:outline-none"
			>
				Delete
			</button>
		</div>
	{/if}
</div>

{#if isEmployee}
	<p
		role="status"
		class="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
	>
		View only — contact an admin to make changes.
	</p>
{/if}

{#if actionErr}
	<p
		role="alert"
		class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
	>
		{actionErr}
	</p>
{/if}

<div class="mt-6 grid gap-6 lg:grid-cols-3">
	<div class="lg:col-span-1">
		<section
			class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
			aria-labelledby="info-h"
		>
			<h2 id="info-h" class="text-base font-semibold text-slate-900">Service info</h2>
			<dl class="mt-4 space-y-4">
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Description</dt>
					<dd class="mt-1 text-sm whitespace-pre-wrap text-slate-900">
						{data.service.description ?? '—'}
					</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Default price</dt>
					<dd class="mt-1 text-sm text-slate-900">{fmtPrice(data.service.default_price)}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Status</dt>
					<dd class="mt-1">
						<StatusBadge status={data.service.is_active ? 'active' : 'inactive'} />
					</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Created</dt>
					<dd class="mt-1 text-sm text-slate-900">{formatDateTime(data.service.created_at)}</dd>
				</div>
				<div>
					<dt class="text-xs font-medium tracking-wide text-slate-500 uppercase">Updated</dt>
					<dd class="mt-1 text-sm text-slate-900">{formatDateTime(data.service.updated_at)}</dd>
				</div>
			</dl>
		</section>
	</div>

	<div class="lg:col-span-2">
		<section
			class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
			aria-labelledby="steps-h"
		>
			<div class="flex items-center justify-between">
				<h2 id="steps-h" class="text-base font-semibold text-slate-900">Milestone steps</h2>
				<span class="text-sm text-slate-500">
					{data.service.steps.length}
					{data.service.steps.length === 1 ? 'step' : 'steps'}
				</span>
			</div>
			{#if data.service.steps.length === 0}
				<p class="mt-4 text-sm text-slate-500">No steps defined.</p>
			{:else}
				<ol class="mt-4 space-y-3">
					{#each data.service.steps as step (step.id)}
						<li class="rounded-md border border-slate-200 bg-slate-50 p-3">
							<div class="flex items-start gap-3">
								<span
									class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700"
									aria-hidden="true"
								>
									{step.sequence_order}
								</span>
								<div class="flex-1">
									<div class="flex flex-wrap items-baseline justify-between gap-2">
										<p class="text-sm font-medium text-slate-900">{step.name}</p>
										{#if step.expected_duration_days !== null && step.expected_duration_days !== undefined}
											<p class="text-xs text-slate-500">
												{step.expected_duration_days}
												{step.expected_duration_days === 1 ? 'day' : 'days'}
											</p>
										{/if}
									</div>
									{#if step.description}
										<p class="mt-1 text-sm text-slate-600">{step.description}</p>
									{/if}
								</div>
							</div>
						</li>
					{/each}
				</ol>
			{/if}
		</section>
	</div>
</div>

<ConfirmDialog
	bind:open={
		() => toggleAction !== null,
		(v) => {
			if (!v) toggleAction = null;
		}
	}
	title={toggleAction === 'activate' ? 'Activate service' : 'Deactivate service'}
	description={toggleAction === 'activate'
		? `${data.service.name} will be available for new projects again.`
		: `${data.service.name} will no longer be available for new projects.`}
	confirmLabel={toggleAction === 'activate' ? 'Activate' : 'Deactivate'}
	busy={toggleBusy}
	onconfirm={runToggle}
/>

<ConfirmDialog
	bind:open={deleteOpen}
	title="Delete service"
	description={`Permanently delete ${data.service.name}? This cannot be undone.`}
	confirmLabel="Delete"
	destructive
	busy={deleteBusy}
	onconfirm={runDelete}
/>
