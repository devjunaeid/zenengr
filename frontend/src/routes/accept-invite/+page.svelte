<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth, homeForRole } from '$lib/stores/auth.svelte.js';

	let { data } = $props();

	let fullName = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let busy = $state(false);
	/** @type {string|null} */
	let error = $state(null);

	const passwordValid = $derived(password.length >= 10);
	const passwordsMatch = $derived(password === confirmPassword);
	const canSubmit = $derived(fullName.trim() && passwordValid && passwordsMatch && !busy);

	/**
	 * @param {string|null|undefined} role
	 */
	function humanizeRole(role) {
		if (role === 'admin') return 'Administrator';
		if (role === 'manager') return 'Manager';
		return 'Employee';
	}

	async function submit() {
		if (!canSubmit) return;
		busy = true;
		error = null;
		try {
			const user = await auth.register(fetch, {
				token: /** @type {string} */ (data.token),
				full_name: fullName.trim(),
				password
			});
			goto(resolve(/** @type {any} */ (homeForRole(user.role))));
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Unable to reach the server. Try again.';
			busy = false;
		}
	}
</script>

<svelte:head><title>Accept invite — ZenEngr</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
	<div class="w-full max-w-sm">
		<div class="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
			<h1 class="text-xl font-semibold text-slate-900">Join your team</h1>

			{#if data.state === 'loading'}
				<div class="mt-4 flex justify-center"><Spinner /></div>
			{:else if data.state === 'invalid'}
				<p class="mt-2 text-sm text-slate-500">
					This invite link is invalid. Please ask your service provider for a new invite.
				</p>
			{:else if data.state === 'expired'}
				<p class="mt-2 text-sm text-slate-500">
					This invite has expired. Ask your administrator to resend the invite.
				</p>
			{:else if data.state === 'accepted'}
				<p class="mt-2 text-sm text-slate-500">This invite has already been accepted.</p>
				<p class="mt-4 text-sm">
					<a href={resolve('/login')} class="font-medium text-indigo-600 hover:text-indigo-500">
						Go to sign in
					</a>
				</p>
			{:else if data.state === 'ready' && data.invite}
				<p class="mt-2 text-sm text-slate-600">
					Join <span class="font-medium">{data.invite.tenant_name}</span> as
					<span class="font-medium">{humanizeRole(data.invite.role)}</span> for
					<span class="font-medium">{data.invite.email}</span>
				</p>

				{#if error}
					<div
						role="alert"
						class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
					>
						{error}
					</div>
				{/if}

				<form
					class="mt-6 space-y-4"
					onsubmit={(e) => {
						e.preventDefault();
						submit();
					}}
				>
					<div>
						<label for="fullName" class="block text-sm font-medium text-slate-700">Full name</label>
						<input
							id="fullName"
							type="text"
							bind:value={fullName}
							required
							autocomplete="name"
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
					<div>
						<label for="password" class="block text-sm font-medium text-slate-700">Password</label>
						<input
							id="password"
							type="password"
							bind:value={password}
							required
							minlength="10"
							autocomplete="new-password"
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
						{#if password && !passwordValid}
							<p class="mt-1 text-xs text-red-600">Minimum 10 characters.</p>
						{/if}
					</div>
					<div>
						<label for="confirmPassword" class="block text-sm font-medium text-slate-700"
							>Confirm password</label
						>
						<input
							id="confirmPassword"
							type="password"
							bind:value={confirmPassword}
							required
							minlength="10"
							autocomplete="new-password"
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
						{#if confirmPassword && !passwordsMatch}
							<p class="mt-1 text-xs text-red-600">Passwords do not match.</p>
						{/if}
					</div>
					<button
						type="submit"
						disabled={!canSubmit}
						aria-busy={busy}
						class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
						Create account
					</button>
				</form>
			{/if}
		</div>
	</div>
</div>
