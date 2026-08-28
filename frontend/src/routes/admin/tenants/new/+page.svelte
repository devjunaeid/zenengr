<script>
	import { untrack } from 'svelte';
	import { resolve } from '$app/paths';
	import * as adminApi from '$lib/api/admin.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { slugify } from '$lib/utils/format.js';

	let { data } = $props();

	let businessName = $state('');
	let slug = $state('');
	let slugTouched = $state(false);
	let planId = $state(untrack(() => data.plans[0]?.id ?? ''));
	let adminEmail = $state('');
	let adminFullName = $state('');
	let adminPassword = $state('');
	let busy = $state(false);
	/** @type {string|null} */
	let error = $state(null);

	/** @type {'idle'|'checking'|'available'|'taken'|'invalid'} */
	let slugState = $state('idle');

	/** @type {{ id: string, business_name: string, slug: string, admin_email: string, temp_password: string }|null} */
	let created = $state(null);
	let copied = $state(false);

	// Live slug availability check, debounced.
	$effect(() => {
		const value = slug.trim();
		if (!value) {
			slugState = 'idle';
			return;
		}
		slugState = 'checking';
		const timer = setTimeout(async () => {
			try {
				const res = await adminApi.slugAvailable(fetch, /** @type {string} */ (auth.token), value);
				slugState = !res.valid ? 'invalid' : res.available ? 'available' : 'taken';
			} catch {
				slugState = 'idle';
			}
		}, 300);
		return () => clearTimeout(timer);
	});

	function onNameInput() {
		if (!slugTouched) slug = slugify(businessName);
	}

	async function submit() {
		if (busy || slugState === 'taken' || slugState === 'invalid') return;
		busy = true;
		error = null;
		try {
			created = await adminApi.createTenant(fetch, /** @type {string} */ (auth.token), {
				business_name: businessName,
				slug: slug.trim(),
				plan_id: planId,
				admin_email: adminEmail,
				admin_full_name: adminFullName,
				...(adminPassword ? { admin_password: adminPassword } : {})
			});
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Unable to reach the server. Try again.';
		} finally {
			busy = false;
		}
	}

	async function copyPassword() {
		if (!created) return;
		try {
			await navigator.clipboard.writeText(created.temp_password);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			/* clipboard unavailable — user can copy manually */
		}
	}
</script>

<svelte:head><title>New tenant — Super Admin</title></svelte:head>

<nav class="text-sm text-slate-500" aria-label="Breadcrumb">
	<a href={resolve('/admin/tenants')} class="text-indigo-600 hover:text-indigo-500">Tenants</a>
	<span aria-hidden="true"> / </span>
	<span>New tenant</span>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">Create tenant</h1>

{#if created}
	<div class="mt-6 max-w-2xl rounded-lg border border-green-200 bg-green-50 p-6" role="status">
		<h2 class="text-lg font-semibold text-green-900">Tenant created</h2>
		<dl class="mt-3 space-y-1 text-sm text-green-900">
			<div>
				<dt class="inline font-medium">Business:</dt>
				<dd class="inline">{created.business_name}</dd>
			</div>
			<div>
				<dt class="inline font-medium">Slug:</dt>
				<dd class="inline font-mono">{created.slug}</dd>
			</div>
			<div>
				<dt class="inline font-medium">Admin email:</dt>
				<dd class="inline">{created.admin_email}</dd>
			</div>
		</dl>
		<div class="mt-4 rounded-md border border-amber-300 bg-amber-50 p-4">
			<p class="text-sm font-medium text-amber-900">
				Temporary password — shown once. Copy it now and share it securely.
			</p>
			<div class="mt-2 flex items-center gap-2">
				<code
					class="rounded bg-white px-3 py-1.5 font-mono text-sm text-slate-900 ring-1 ring-amber-300"
				>
					{created.temp_password}
				</code>
				<button
					type="button"
					onclick={copyPassword}
					class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
				>
					{copied ? 'Copied' : 'Copy'}
				</button>
			</div>
		</div>
		<div class="mt-4 flex gap-3">
			<a
				href={resolve('/admin/tenants/[id]', { id: created.id })}
				class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
			>
				Open tenant
			</a>
			<a
				href={resolve('/admin/tenants')}
				class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
			>
				Back to list
			</a>
		</div>
	</div>
{:else}
	{#if error}
		<div
			role="alert"
			class="mt-4 max-w-2xl rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
		>
			{error}
		</div>
	{/if}

	<form
		class="mt-6 max-w-2xl space-y-5 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
		onsubmit={(e) => {
			e.preventDefault();
			submit();
		}}
	>
		<div>
			<label for="business_name" class="block text-sm font-medium text-slate-700">
				Business name
			</label>
			<input
				id="business_name"
				type="text"
				bind:value={businessName}
				oninput={onNameInput}
				required
				maxlength="255"
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>

		<div>
			<label for="slug" class="block text-sm font-medium text-slate-700">Slug</label>
			<input
				id="slug"
				type="text"
				bind:value={slug}
				oninput={() => (slugTouched = true)}
				required
				pattern="[a-z0-9\-]+"
				aria-describedby="slug-status"
				class="mt-1 block w-full rounded-md border-slate-300 font-mono text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
			<p id="slug-status" class="mt-1 text-xs" aria-live="polite">
				{#if slugState === 'checking'}
					<span class="text-slate-500">Checking availability…</span>
				{:else if slugState === 'available'}
					<span class="text-green-700">Slug is available.</span>
				{:else if slugState === 'taken'}
					<span class="text-red-700">Slug is already taken.</span>
				{:else if slugState === 'invalid'}
					<span class="text-red-700"
						>Slug format is invalid (lowercase letters, numbers, dashes).</span
					>
				{:else}
					<span class="text-slate-500">Lowercase letters, numbers and dashes.</span>
				{/if}
			</p>
		</div>

		<div>
			<label for="plan" class="block text-sm font-medium text-slate-700">Plan</label>
			<select
				id="plan"
				bind:value={planId}
				required
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			>
				{#each data.plans as plan (plan.id)}
					<option value={plan.id}>{plan.name}</option>
				{/each}
			</select>
		</div>

		<div class="grid gap-5 sm:grid-cols-2">
			<div>
				<label for="admin_full_name" class="block text-sm font-medium text-slate-700">
					Admin full name
				</label>
				<input
					id="admin_full_name"
					type="text"
					bind:value={adminFullName}
					required
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="admin_email" class="block text-sm font-medium text-slate-700">
					Admin email
				</label>
				<input
					id="admin_email"
					type="email"
					bind:value={adminEmail}
					required
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
		</div>

		<div>
			<label for="admin_password" class="block text-sm font-medium text-slate-700">
				Admin password
				<span class="ml-1 text-xs font-normal text-slate-400">(leave blank to auto-generate)</span>
			</label>
			<input
				id="admin_password"
				type="password"
				bind:value={adminPassword}
				minlength="8"
				maxlength="128"
				autocomplete="new-password"
				placeholder="Min 8 characters, or leave blank"
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
			{#if adminPassword && adminPassword.length < 8}
				<p class="mt-1 text-xs text-red-600">Password must be at least 8 characters.</p>
			{/if}
		</div>

		<div class="flex items-center gap-3 border-t border-slate-200 pt-5">
			<button
				type="submit"
				disabled={busy || slugState === 'taken' || slugState === 'invalid'}
				aria-busy={busy}
				class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
				Create tenant
			</button>
			<a
				href={resolve('/admin/tenants')}
				class="text-sm font-medium text-slate-600 hover:text-slate-500"
			>
				Cancel
			</a>
		</div>
	</form>
{/if}
