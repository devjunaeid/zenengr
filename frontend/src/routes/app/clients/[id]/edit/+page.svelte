<script>
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as clientApi from '$lib/api/clients.js';
	import AddressFields from '$lib/components/AddressFields.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { addressToFields, fieldsToAddress } from '$lib/utils/address.js';
	import { humanize } from '$lib/utils/format.js';

	let { data } = $props();

	const token = auth.token;
	const client = untrack(() => data.client);

	let name = $state(client.name);
	let clientType = $state(client.client_type);
	let email = $state(client.email ?? '');
	let phone = $state(client.phone ?? '');
	let taxId = $state(client.tax_id ?? '');
	let addressFields = $state(addressToFields(client.billing_address));
	let tags = $state([...client.tags]);
	let tagInput = $state('');
	let busy = $state(false);
	let err = $state(null);

	function addTag() {
		const t = tagInput.trim();
		if (!t) return;
		if (!tags.includes(t)) tags = [...tags, t];
		tagInput = '';
	}

	function removeTag(t) {
		tags = tags.filter((x) => x !== t);
	}

	function onTagKeydown(e) {
		if (e.key === 'Enter' || e.key === ',') {
			e.preventDefault();
			addTag();
		} else if (e.key === 'Backspace' && !tagInput && tags.length) {
			tags = tags.slice(0, -1);
		}
	}

	async function submit() {
		busy = true;
		err = null;
		try {
			const body = {
				name,
				client_type: clientType,
				email: email.trim() || null,
				phone: phone.trim() || null,
				tax_id: taxId.trim() || null,
				tags
			};
			body.billing_address = fieldsToAddress(addressFields);
			await clientApi.updateClient(fetch, token, client.id, body);
			goto(resolve('/app/clients/[id]', { id: client.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Save failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Edit {client.name} — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex flex-wrap items-center gap-1">
		<li>
			<a href={resolve('/app/clients')} class="hover:text-indigo-600">Clients</a>
		</li>
		<li aria-hidden="true">/</li>
		<li>
			<a href={resolve('/app/clients/[id]', { id: client.id })} class="hover:text-indigo-600"
				>{client.name}</a
			>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">Edit</li>
	</ol>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">Edit client</h1>

<p class="mt-1 text-sm text-slate-500">
	Current status: <span class="font-medium">{humanize(client.status)}</span>. To change status, use
	Archive / Unarchive on the client detail page.
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
		<label for="c-name" class="block text-sm font-medium text-slate-700">Name *</label>
		<input
			id="c-name"
			type="text"
			bind:value={name}
			required
			maxlength="255"
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>

	<fieldset>
		<legend class="block text-sm font-medium text-slate-700">Type</legend>
		<div class="mt-2 flex gap-4">
			<label class="inline-flex items-center gap-2 text-sm text-slate-700">
				<input
					type="radio"
					name="client_type"
					value="company"
					checked={clientType === 'company'}
					onchange={() => (clientType = 'company')}
					class="border-slate-300 text-indigo-600 focus:ring-indigo-500"
				/>
				Company
			</label>
			<label class="inline-flex items-center gap-2 text-sm text-slate-700">
				<input
					type="radio"
					name="client_type"
					value="individual"
					checked={clientType === 'individual'}
					onchange={() => (clientType = 'individual')}
					class="border-slate-300 text-indigo-600 focus:ring-indigo-500"
				/>
				Individual
			</label>
		</div>
	</fieldset>

	<div class="grid gap-4 sm:grid-cols-2">
		<div>
			<label for="c-email" class="block text-sm font-medium text-slate-700">Email</label>
			<input
				id="c-email"
				type="email"
				bind:value={email}
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>
		<div>
			<label for="c-phone" class="block text-sm font-medium text-slate-700">Phone</label>
			<input
				id="c-phone"
				type="text"
				bind:value={phone}
				class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
			/>
		</div>
	</div>

	<div>
		<label for="c-tax" class="block text-sm font-medium text-slate-700">Tax ID</label>
		<input
			id="c-tax"
			type="text"
			bind:value={taxId}
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
	</div>

	<div>
		<span class="block text-sm font-medium text-slate-700">Billing address</span>
		<div class="mt-1">
			<AddressFields bind:fields={addressFields} idPrefix="c" />
		</div>
		<p class="mt-1 text-xs text-slate-500">All fields optional. Leave blank to clear.</p>
	</div>

	<div>
		<label for="c-tags" class="block text-sm font-medium text-slate-700">Tags</label>
		<input
			id="c-tags"
			type="text"
			bind:value={tagInput}
			onkeydown={onTagKeydown}
			onblur={addTag}
			placeholder="Type and press Enter or comma"
			class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
		/>
		{#if tags.length}
			<div class="mt-2 flex flex-wrap gap-1">
				{#each tags as t (t)}
					<span
						class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-300 ring-inset"
					>
						{t}
						<button
							type="button"
							onclick={() => removeTag(t)}
							aria-label={`Remove tag ${t}`}
							class="text-slate-500 hover:text-slate-700"
						>
							×
						</button>
					</span>
				{/each}
			</div>
		{/if}
		<p class="mt-1 text-xs text-slate-500">Press Enter or comma to add a tag.</p>
	</div>

	<div class="flex flex-wrap items-center gap-3 pt-2">
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
			href={resolve('/app/clients/[id]', { id: client.id })}
			class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Cancel
		</a>
	</div>
</form>
