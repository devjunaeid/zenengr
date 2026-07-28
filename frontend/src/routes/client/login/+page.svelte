<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { portalAuth } from '$lib/stores/portalAuth.svelte.js';

	let email = $state('');
	let password = $state('');
	let busy = $state(false);
	/** @type {string|null} */
	let error = $state(null);

	async function submit() {
		if (busy) return;
		busy = true;
		error = null;
		try {
			await portalAuth.login(fetch, email, password);
			goto(resolve('/client'));
		} catch (e) {
			if (e instanceof ApiError) {
				// Map specific backend error codes/messages
				if (e.status === 403 && e.message.includes('archived')) {
					error = 'Your client account has been archived. Contact your service provider.';
				} else if (e.status === 403 && e.message.includes('suspended')) {
					error = 'This account has been suspended. Contact support.';
				} else if (e.status === 403 && e.message.includes('cancelled')) {
					error = 'This account has been cancelled. Contact support.';
				} else {
					error = e.message;
				}
			} else {
				error = 'Unable to reach the server. Try again.';
			}
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Client sign in — ZenEngr</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
	<div class="w-full max-w-sm">
		<div class="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
			<h1 class="text-xl font-semibold text-slate-900">Client sign in</h1>
			<p class="mt-1 text-sm text-slate-500">Access your projects, invoices, and profile.</p>

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
					<label for="password" class="block text-sm font-medium text-slate-700">Password</label>
					<input
						id="password"
						type="password"
						bind:value={password}
						required
						autocomplete="current-password"
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
					Sign in
				</button>
			</form>
		</div>
		<p class="mt-4 text-center text-sm text-slate-500">
			Staff user? <a
				href={resolve('/login')}
				class="font-medium text-indigo-600 hover:text-indigo-500">Staff sign in</a
			>
		</p>
	</div>
</div>
