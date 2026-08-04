<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import * as accountApi from '$lib/api/account.js';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';

	const token = page.url.searchParams.get('token');

	let newPassword = $state('');
	let confirmPassword = $state('');
	let busy = $state(false);
	let done = $state(false);
	/** @type {string|null} */
	let error = $state(null);

	async function submit() {
		if (busy) return;
		error = null;
		if (newPassword.length < 8) {
			error = 'New password must be at least 8 characters.';
			return;
		}
		if (newPassword !== confirmPassword) {
			error = 'New password and confirmation do not match.';
			return;
		}
		busy = true;
		try {
			await accountApi.resetPassword(
				fetch,
				{ token: /** @type {string} */ (token), new_password: newPassword },
				{ realm: 'client' }
			);
			done = true;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Unable to reach the server. Try again.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Reset password — Client Portal</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
	<div class="w-full max-w-sm">
		<div class="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
			{#if !token}
				<h1 class="text-xl font-semibold text-slate-900">Reset password</h1>
				<div
					role="alert"
					class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
				>
					This reset link is missing its token. Use the link from your email.
				</div>
			{:else if done}
				<h1 class="text-xl font-semibold text-slate-900">Password updated</h1>
				<div
					role="status"
					class="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
				>
					Your password has been reset. You can now sign in.
				</div>
				<p class="mt-6 text-center text-sm text-slate-500">
					<a
						href={resolve('/client/login')}
						class="font-medium text-indigo-600 hover:text-indigo-500">Go to sign in</a
					>
				</p>
			{:else}
				<h1 class="text-xl font-semibold text-slate-900">Reset password</h1>
				<p class="mt-1 text-sm text-slate-500">Choose a new password (minimum 8 characters).</p>

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
						<label for="crp-new" class="block text-sm font-medium text-slate-700"
							>New password</label
						>
						<input
							id="crp-new"
							type="password"
							bind:value={newPassword}
							required
							minlength="8"
							autocomplete="new-password"
							class="mt-1 block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
						/>
					</div>
					<div>
						<label for="crp-confirm" class="block text-sm font-medium text-slate-700"
							>Confirm new password</label
						>
						<input
							id="crp-confirm"
							type="password"
							bind:value={confirmPassword}
							required
							minlength="8"
							autocomplete="new-password"
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
						Reset password
					</button>
				</form>
			{/if}
		</div>
	</div>
</div>
