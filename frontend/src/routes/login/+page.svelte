<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError } from '$lib/api/client.js';
	import Spinner from '$lib/components/Spinner.svelte';
	import { auth, homeForRole } from '$lib/stores/auth.svelte.js';

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
			const user = await auth.login(fetch, email, password);
			goto(resolve(/** @type {any} */ (homeForRole(user.role))));
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Unable to reach the server. Try again.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Sign in — ZenEngr</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
	<div class="w-full max-w-sm">
		<div class="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
			<h1 class="text-xl font-semibold text-slate-900">Staff sign in</h1>
			<p class="mt-1 text-sm text-slate-500">ZenEngr platform — admin and staff access.</p>

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
					<div class="mt-1 text-right">
						<a
							href={resolve('/forgot-password')}
							class="text-xs font-medium text-indigo-600 hover:text-indigo-500">Forgot password?</a
						>
					</div>
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
			Client user? <a
				href={resolve('/client/login')}
				class="font-medium text-indigo-600 hover:text-indigo-500">Go to the client portal</a
			>
		</p>
	</div>
</div>
