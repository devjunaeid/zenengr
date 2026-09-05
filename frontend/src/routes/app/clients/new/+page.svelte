<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import * as clientApi from '$lib/api/clients.js';
	import AddressFields from '$lib/components/AddressFields.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { fieldsToAddress } from '$lib/utils/address.js';

	const token = auth.token;

	let name = $state('');
	let clientType = $state('company');
	let email = $state('');
	let phone = $state('');
	let taxId = $state('');
	let clientUserEmail = $state('');
	let clientUserPassword = $state('');
	let showPassword = $state(false);
	let addressFields = $state({
		address_line1: '',
		address_line2: '',
		city: '',
		state: '',
		postal_code: '',
		country: ''
	});
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

	function generatePortalPassword() {
		const chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*';
		let pass = '';
		for (let i = 0; i < 12; i++) {
			pass += chars.charAt(Math.floor(Math.random() * chars.length));
		}
		clientUserPassword = pass;
		showPassword = true;
	}

	async function submit() {
		busy = true;
		err = null;
		try {
			const body = {
				name,
				client_type: clientType,
				...(email.trim() && { email: email.trim() }),
				...(phone.trim() && { phone: phone.trim() }),
				...(taxId.trim() && { tax_id: taxId.trim() }),
				...(tags.length && { tags }),
				...(clientUserEmail.trim() && { client_user_email: clientUserEmail.trim() }),
				...(clientUserPassword && { client_user_password: clientUserPassword })
			};
			const billingAddress = fieldsToAddress(addressFields);
			if (Object.keys(billingAddress).length) body.billing_address = billingAddress;
			const created = await clientApi.createClient(fetch, token, body);
			goto(resolve('/app/clients/[id]', { id: created.id }));
		} catch (e) {
			err = e instanceof ApiError ? e.message : 'Create failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>New Client — ZenEngr</title></svelte:head>

<div class="mx-auto max-w-3xl pb-12">
	<!-- Top Breadcrumb & Header -->
	<div class="mb-6">
		<nav aria-label="Breadcrumb" class="text-xs font-medium text-slate-500">
			<ol class="flex flex-wrap items-center gap-1.5">
				<li>
					<a href={resolve('/app/clients')} class="transition-colors hover:text-indigo-600"
						>Clients</a
					>
				</li>
				<li aria-hidden="true" class="text-slate-300">/</li>
				<li class="font-semibold text-slate-800">New Client</li>
			</ol>
		</nav>
		<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-2xl font-bold tracking-tight text-slate-900">Create New Client</h1>
				<p class="mt-1 text-sm text-slate-500">
					Add client business profile, billing address, and optional portal credentials.
				</p>
			</div>
		</div>
	</div>

	{#if err}
		<div
			role="alert"
			class="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 shadow-2xs"
		>
			<svg
				class="mt-0.5 h-5 w-5 shrink-0 text-red-500"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
			<div>
				<span class="font-semibold">Unable to create client:</span>
				<p class="mt-0.5">{err}</p>
			</div>
		</div>
	{/if}

	<form
		class="space-y-6"
		onsubmit={(e) => {
			e.preventDefault();
			submit();
		}}
	>
		<!-- ── 1. Basic Information ───────────────────────────────────────────── -->
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<div class="flex items-center gap-2.5 border-b border-slate-100 pb-4">
				<div
					class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"
				>
					<svg
						class="h-4 w-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
						/>
					</svg>
				</div>
				<div>
					<h2 class="text-base font-semibold text-slate-900">Client Details</h2>
					<p class="text-xs text-slate-500">Essential business identity and contact details.</p>
				</div>
			</div>

			<div class="mt-5 space-y-4">
				<!-- Name -->
				<div>
					<label
						for="c-name"
						class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
					>
						Client Name <span class="text-red-500">*</span>
					</label>
					<input
						id="c-name"
						type="text"
						bind:value={name}
						placeholder="Acme Corporation or John Doe"
						required
						maxlength="255"
						class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>

				<!-- Client Type Cards -->
				<div>
					<span class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>Account Type</span
					>
					<div class="mt-1.5 grid grid-cols-1 gap-3 sm:grid-cols-2">
						<label
							class="flex cursor-pointer items-center justify-between rounded-lg border p-3 transition-all {clientType ===
							'company'
								? 'border-indigo-600 bg-indigo-50/40 ring-1 ring-indigo-600'
								: 'border-slate-200 hover:border-slate-300'}"
						>
							<div class="flex items-center gap-2.5">
								<input
									type="radio"
									name="client_type"
									value="company"
									checked={clientType === 'company'}
									onchange={() => (clientType = 'company')}
									class="h-4 w-4 border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
								<div>
									<span class="block text-sm font-medium text-slate-900">Company / Org</span>
									<span class="block text-xs text-slate-500">Business or enterprise</span>
								</div>
							</div>
							<svg
								class="h-5 w-5 text-slate-400"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="1.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16"
								/>
							</svg>
						</label>

						<label
							class="flex cursor-pointer items-center justify-between rounded-lg border p-3 transition-all {clientType ===
							'individual'
								? 'border-indigo-600 bg-indigo-50/40 ring-1 ring-indigo-600'
								: 'border-slate-200 hover:border-slate-300'}"
						>
							<div class="flex items-center gap-2.5">
								<input
									type="radio"
									name="client_type"
									value="individual"
									checked={clientType === 'individual'}
									onchange={() => (clientType = 'individual')}
									class="h-4 w-4 border-slate-300 text-indigo-600 focus:ring-indigo-500"
								/>
								<div>
									<span class="block text-sm font-medium text-slate-900">Individual</span>
									<span class="block text-xs text-slate-500">Freelancer or solo</span>
								</div>
							</div>
							<svg
								class="h-5 w-5 text-slate-400"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="1.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
								/>
							</svg>
						</label>
					</div>
				</div>

				<!-- Email & Phone Grid -->
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label
							for="c-email"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							Contact Email
						</label>
						<input
							id="c-email"
							type="email"
							bind:value={email}
							placeholder="billing@client.com"
							class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
					<div>
						<label
							for="c-phone"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							Phone Number
						</label>
						<input
							id="c-phone"
							type="text"
							bind:value={phone}
							placeholder="+1 (555) 000-0000"
							class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
				</div>

				<!-- Tax ID -->
				<div>
					<label
						for="c-tax"
						class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
					>
						Tax ID / VAT / Business Number
					</label>
					<input
						id="c-tax"
						type="text"
						bind:value={taxId}
						placeholder="e.g. EU123456789 or EIN-1234567"
						class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
			</div>
		</section>

		<!-- ── 2. Billing Address ─────────────────────────────────────────────── -->
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<div class="flex items-center gap-2.5 border-b border-slate-100 pb-4">
				<div
					class="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600"
				>
					<svg
						class="h-4 w-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
						/>
					</svg>
				</div>
				<div>
					<h2 class="text-base font-semibold text-slate-900">Billing Address</h2>
					<p class="text-xs text-slate-500">Official invoice and receipt delivery address.</p>
				</div>
			</div>

			<div class="mt-5">
				<AddressFields bind:fields={addressFields} idPrefix="c" />
			</div>
		</section>

		<!-- ── 3. Tags & Categorization ───────────────────────────────────────── -->
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<div class="flex items-center gap-2.5 border-b border-slate-100 pb-4">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
					<svg
						class="h-4 w-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
						/>
					</svg>
				</div>
				<div>
					<h2 class="text-base font-semibold text-slate-900">Tags & Categorization</h2>
					<p class="text-xs text-slate-500">
						Label and group this client (e.g. VIP, Retainer, Enterprise).
					</p>
				</div>
			</div>

			<div class="mt-5">
				<label
					for="c-tags"
					class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
					>Add Tags</label
				>
				<div class="mt-1.5">
					<input
						id="c-tags"
						type="text"
						bind:value={tagInput}
						onkeydown={onTagKeydown}
						onblur={addTag}
						placeholder="Type tag name and press Enter or comma..."
						class="block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
					/>
				</div>
				{#if tags.length}
					<div class="mt-3 flex flex-wrap gap-1.5">
						{#each tags as t (t)}
							<span
								class="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 ring-1 ring-indigo-200"
							>
								{t}
								<button
									type="button"
									onclick={() => removeTag(t)}
									aria-label={`Remove tag ${t}`}
									class="text-indigo-400 transition-colors hover:text-indigo-700"
								>
									<svg
										class="h-3 w-3"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
										stroke-width="2"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</span>
						{/each}
					</div>
				{/if}
			</div>
		</section>

		<!-- ── 4. Client Portal Access ────────────────────────────────────────── -->
		<section class="rounded-xl border border-slate-200 bg-white p-6 shadow-2xs">
			<div class="flex items-center gap-2.5 border-b border-slate-100 pb-4">
				<div
					class="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-50 text-purple-600"
				>
					<svg
						class="h-4 w-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
						/>
					</svg>
				</div>
				<div>
					<h2 class="text-base font-semibold text-slate-900">Client Portal Login</h2>
					<p class="text-xs text-slate-500">
						Provide direct login access for this client (optional).
					</p>
				</div>
			</div>

			<div class="mt-5 space-y-4">
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label
							for="c-user-email"
							class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
						>
							Portal User Email
						</label>
						<input
							id="c-user-email"
							type="email"
							bind:value={clientUserEmail}
							placeholder="portal-login@client.com"
							autocomplete="email"
							class="mt-1.5 block w-full rounded-lg border-slate-300 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>

					<div>
						<div class="flex items-center justify-between">
							<label
								for="c-user-password"
								class="block text-xs font-semibold tracking-wider text-slate-700 uppercase"
							>
								Portal Password
							</label>
							<button
								type="button"
								onclick={generatePortalPassword}
								class="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
							>
								Auto-generate
							</button>
						</div>
						<div class="relative mt-1.5">
							<input
								id="c-user-password"
								type={showPassword ? 'text' : 'password'}
								bind:value={clientUserPassword}
								placeholder="Minimum 10 characters"
								minlength="10"
								autocomplete="new-password"
								class="block w-full rounded-lg border-slate-300 pr-12 text-sm shadow-2xs focus:border-indigo-500 focus:ring-indigo-500"
							/>
							<button
								type="button"
								onclick={() => (showPassword = !showPassword)}
								class="absolute inset-y-0 right-0 flex items-center pr-3 text-xs font-medium text-slate-400 hover:text-slate-600"
							>
								{showPassword ? 'Hide' : 'Show'}
							</button>
						</div>
					</div>
				</div>
				<p class="text-xs text-slate-500">
					Leave blank if this client does not require portal access yet.
				</p>
			</div>
		</section>

		<!-- ── Form Actions ────────────────────────────────────────────────────── -->
		<div class="flex flex-wrap items-center justify-end gap-3 border-t border-slate-200 pt-4">
			<a
				href={resolve('/app/clients')}
				class="rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
			>
				Cancel
			</a>
			<button
				type="submit"
				disabled={busy}
				aria-busy={busy}
				class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
			>
				{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
				Create Client
			</button>
		</div>
	</form>
</div>
