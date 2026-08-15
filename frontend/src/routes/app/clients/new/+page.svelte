<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as clientApi from '$lib/api/clients.js';
	import AddressFields from '$lib/components/AddressFields.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { fieldsToAddress } from '$lib/utils/address.js';

	const token = /** @type {string} */ (auth.token);

	let name = $state('');
	let clientType = $state('company');
	let email = $state('');
	let phone = $state('');
	let taxId = $state('');
	let clientUserEmail = $state('');
	let clientUserPassword = $state('');
	/** @type {import('$lib/utils/address.js').AddressFields} */
	let addressFields = $state({
		address_line1: '',
		address_line2: '',
		city: '',
		state: '',
		postal_code: '',
		country: ''
	});
	/** @type {string[]} */
	let tags = $state([]);
	let tagInput = $state('');
	let busy = $state(false);
	/** @type {string|null} */
	let err = $state(null);

	function addTag() {
		const t = tagInput.trim();
		if (!t) return;
		if (!tags.includes(t)) tags = [...tags, t];
		tagInput = '';
	}

	/** @param {string} t */
	function removeTag(t) {
		tags = tags.filter((x) => x !== t);
	}

	/** @param {KeyboardEvent} e */
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
			/** @type {Record<string, any>} */
			const body = {
				name,
				client_type: /** @type {'company'|'individual'} */ (clientType),
				...(email.trim() && { email: email.trim() }),
				...(phone.trim() && { phone: phone.trim() }),
				...(taxId.trim() && { tax_id: taxId.trim() }),
				...(tags.length && { tags }),
				...(clientUserEmail.trim() && { client_user_email: clientUserEmail.trim() }),
				...(clientUserPassword && { client_user_password: clientUserPassword })
			};
			const billingAddress = fieldsToAddress(addressFields);
			if (Object.keys(billingAddress).length) body.billing_address = billingAddress;
			const created = await clientApi.createClient(fetch, token, /** @type {any} */ (body));
			goto(resolve('/app/clients/[id]', { id: created.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Create failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>New client — ZenEngr</title></svelte:head>

<nav aria-label="Breadcrumb" class="text-sm text-slate-500">
	<ol class="flex items-center gap-1">
		<li>
			<a href={resolve('/app/clients')} class="hover:text-indigo-600">Clients</a>
		</li>
		<li aria-hidden="true">/</li>
		<li class="font-medium text-slate-700">New</li>
	</ol>
</nav>

<h1 class="mt-2 text-2xl font-semibold text-slate-900">New client</h1>

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
		<p class="mt-1 text-xs text-slate-500">All fields optional.</p>
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

	<div class="rounded-md border border-slate-200 bg-slate-50/50 p-4">
		<span class="block text-sm font-medium text-slate-900">Client user</span>
		<p class="mt-1 text-xs text-slate-500">
			This user will be the primary billing contact and can sign in to the client portal.
		</p>
		<div class="mt-4 grid gap-4 sm:grid-cols-2">
			<div>
				<label for="c-user-email" class="block text-sm font-medium text-slate-700">Email *</label>
				<input
					id="c-user-email"
					type="email"
					bind:value={clientUserEmail}
					required
					autocomplete="email"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="c-user-password" class="block text-sm font-medium text-slate-700"
					>Password *</label
				>
				<input
					id="c-user-password"
					type="password"
					bind:value={clientUserPassword}
					required
					minlength="10"
					autocomplete="new-password"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
		</div>
		<p class="mt-1 text-xs text-slate-500">Password must be at least 10 characters.</p>
	</div>

	<div class="flex items-center gap-3 pt-2">
		<button
			type="submit"
			disabled={busy}
			aria-busy={busy}
			class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
		>
			{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
			Create client
		</button>
		<a
			href={resolve('/app/clients')}
			class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
		>
			Cancel
		</a>
	</div>
</form>
