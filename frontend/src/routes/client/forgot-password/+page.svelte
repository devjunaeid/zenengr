<script>
	import { resolve } from '$app/paths';
	import * as accountApi from '$lib/api/account.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';

	let email = $state('');
	let busy = $state(false);
	let sent = $state(false);
	/** @type {string|null} */
	let error = $state(null);

	async function submit() {
		if (busy) return;
		busy = true;
		error = null;
		try {
			await accountApi.forgotPassword(fetch, email.trim(), { realm: 'client' });
			sent = true;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Unable to reach the server. Try again.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Forgot password — Client Portal</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
	<div class="w-full max-w-sm">
		<div class="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
			<h1 class="text-xl font-semibold text-slate-900">Forgot password</h1>
			<p class="mt-1 text-sm text-slate-500">Enter your email to receive a reset link.</p>

			{#if sent}
				<div
					role="status"
					class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
				>
					If an account exists, a reset link was sent.
				</div>
				<p class="mt-6 text-center text-sm text-slate-500">
					<a
						href={resolve('/client/login')}
						class="font-medium text-indigo-600 hover:text-indigo-500">Back to sign in</a
					>
				</p>
			{:else}
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
						<label for="cfp-email" class="block text-sm font-medium text-slate-700">Email</label>
						<input
							id="cfp-email"
							type="email"
							bind:value={email}
							required
							autocomplete="email"
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
					<button
						type="submit"
						disabled={busy}
						aria-busy={busy}
						class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
					>
						{#if busy}<Spinner class="h-4 w-4 text-white" />{/if}
						Send reset link
					</button>
				</form>
				<p class="mt-4 text-center text-sm text-slate-500">
					<a
						href={resolve('/client/login')}
						class="font-medium text-indigo-600 hover:text-indigo-500">Back to sign in</a
					>
				</p>
			{/if}
		</div>
	</div>
</div>
