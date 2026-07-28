<script>
	import { ApiError } from '$lib/api/client.js';
	import * as portalApi from '$lib/api/portal.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

	// Layout guard guarantees these exist
	const client = /** @type {import('$lib/api/portal.js').PortalClient} */ (portalAuth.client);

	// Contact edit state
	let email = $state(client.email ?? '');
	let phone = $state(client.phone ?? '');
	let saving = $state(false);
	/** @type {string|null} */
	let saveError = $state(null);
	/** @type {string|null} */
	let saveSuccess = $state(null);

	async function saveContact() {
		if (saving) return;
		saving = true;
		saveError = null;
		saveSuccess = null;
		try {
			const fields = {};
			if (email !== (client.email ?? '')) fields.email = email;
			if (phone !== (client.phone ?? '')) fields.phone = phone;
			if (Object.keys(fields).length === 0) {
				saveSuccess = 'No changes to save.';
				saving = false;
				return;
			}
			await portalApi.updateProfile(fetch, /** @type {string} */ (portalAuth.token), fields);
			// Refresh client data in store
			const me = await portalApi.me(fetch, /** @type {string} */ (portalAuth.token));
			// Update local reference
			if (portalAuth.client) {
				portalAuth.client.email = me.client.email;
				portalAuth.client.phone = me.client.phone;
			}
			saveSuccess = 'Contact details updated.';
		} catch (e) {
			if (e instanceof ApiError) {
				saveError = e.message;
			} else {
				saveError = 'Unable to save. Try again.';
			}
		} finally {
			saving = false;
		}
	}

	/**
	 * Render billing address as readable lines.
	 * @param {Record<string,any>|null} addr
	 */
	function renderAddress(addr) {
		if (!addr) return '—';
		const parts = [];
		if (addr.line1) parts.push(addr.line1);
		if (addr.line2) parts.push(addr.line2);
		if (addr.city || addr.state || addr.postal_code) {
			parts.push([addr.city, addr.state, addr.postal_code].filter(Boolean).join(', '));
		}
		if (addr.country) parts.push(addr.country);
		return parts.length ? parts.join('\n') : '—';
	}
</script>

<svelte:head><title>Profile — Client Portal</title></svelte:head>

<div class="space-y-6">
	<h1 class="text-xl font-semibold text-slate-900">Profile</h1>

	<!-- Contact details card -->
	<div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
		<h2 class="text-base font-semibold text-slate-900">Contact details</h2>
		<p class="mt-1 text-sm text-slate-500">Update your email and phone number.</p>

		{#if saveError}
			<div
				role="alert"
				class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
			>
				{saveError}
			</div>
		{/if}
		{#if saveSuccess}
			<div
				role="status"
				class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
			>
				{saveSuccess}
			</div>
		{/if}

		<form
			class="mt-4 space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				saveContact();
			}}
		>
			<div>
				<label for="email" class="block text-sm font-medium text-slate-700">Email</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					required
					autocomplete="email"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="phone" class="block text-sm font-medium text-slate-700">Phone</label>
				<input
					id="phone"
					type="tel"
					bind:value={phone}
					autocomplete="tel"
					class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<button
					type="submit"
					disabled={saving}
					aria-busy={saving}
					class="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if saving}<Spinner class="h-4 w-4 text-white" />{/if}
					Save changes
				</button>
			</div>
		</form>
	</div>

	<!-- Billing details card (read-only) -->
	<div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
		<h2 class="text-base font-semibold text-slate-900">Billing details</h2>
		<p class="mt-1 text-sm text-slate-500">
			Read-only. Contact your agency to change billing details.
		</p>

		<dl class="mt-4 space-y-3">
			<div>
				<dt class="text-sm font-medium text-slate-500">Client name</dt>
				<dd class="mt-0.5 text-sm text-slate-900">{client.name}</dd>
			</div>
			<div>
				<dt class="text-sm font-medium text-slate-500">Billing address</dt>
				<dd class="mt-0.5 text-sm whitespace-pre-line text-slate-900">
					{renderAddress(client.billing_address)}
				</dd>
			</div>
			<div>
				<dt class="text-sm font-medium text-slate-500">Tax ID</dt>
				<dd class="mt-0.5 text-sm text-slate-900">{client.tax_id ?? '—'}</dd>
			</div>
		</dl>

		<p class="mt-4 text-xs text-slate-400">
			Need to change billing info? Contact your service provider.
		</p>
	</div>
</div>
