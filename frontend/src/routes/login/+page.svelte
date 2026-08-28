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

<svelte:head><title>Staff Sign In — ZenEngr</title></svelte:head>

<div class="login-root">
	<!-- Left panel: branding -->
	<div class="brand-panel">
		<div class="brand-inner">
			<div class="brand-logo">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="brand-logo-icon">
					<path fill-rule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 00.374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.39-.223-2.73-.635-3.985a.75.75 0 00-.722-.516l-.143.001c-2.996 0-5.717-1.17-7.734-3.08z" clip-rule="evenodd" />
				</svg>
			</div>
			<h2 class="brand-title">ZenEngr</h2>
			<p class="brand-subtitle">Internal Platform</p>

			<div class="brand-features">
				<div class="brand-feature">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="feature-icon">
						<path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />
					</svg>
					<span>Team & client management</span>
				</div>
				<div class="brand-feature">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="feature-icon">
						<path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd" />
					</svg>
					<span>Invoicing & billing</span>
				</div>
				<div class="brand-feature">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="feature-icon">
						<path d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm8-5a.75.75 0 01.75.75v4.5l2.857 1.714a.75.75 0 01-.75 1.286l-3.25-1.95a.75.75 0 01-.357-.643V5.75A.75.75 0 0110 5z" />
					</svg>
					<span>Project tracking & reporting</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Right panel: form -->
	<div class="form-panel">
		<div class="form-card">
			<!-- Role badge -->
			<div class="role-badge staff">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="role-icon">
					<path fill-rule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 00.374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.39-.223-2.73-.635-3.985a.75.75 0 00-.722-.516l-.143.001c-2.996 0-5.717-1.17-7.734-3.08z" clip-rule="evenodd" />
				</svg>
				Staff Portal
			</div>

			<h1 class="form-title">Welcome back</h1>
			<p class="form-subtitle">Sign in to manage your workspace.</p>

			{#if error}
				<div role="alert" class="error-box">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="error-icon">
						<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
					</svg>
					{error}
				</div>
			{/if}

			<form
				class="form-body"
				onsubmit={(e) => {
					e.preventDefault();
					submit();
				}}
			>
				<div class="field">
					<label for="email" class="field-label">Email address</label>
					<div class="input-wrap">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="input-icon">
							<path d="M3 4a2 2 0 00-2 2v1.161l8.441 4.221a1.25 1.25 0 001.118 0L19 7.162V6a2 2 0 00-2-2H3z" />
							<path d="M19 8.839l-7.77 3.885a2.75 2.75 0 01-2.46 0L1 8.839V14a2 2 0 002 2h14a2 2 0 002-2V8.839z" />
						</svg>
						<input
							id="email"
							type="email"
							bind:value={email}
							required
							autocomplete="email"
							placeholder="you@company.com"
							class="input-field"
						/>
					</div>
				</div>
				<div class="field">
					<label for="password" class="field-label">Password</label>
					<div class="input-wrap">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="input-icon">
							<path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd" />
						</svg>
						<input
							id="password"
							type="password"
							bind:value={password}
							required
							autocomplete="current-password"
							placeholder="••••••••"
							class="input-field"
						/>
					</div>
					<div class="forgot-wrap">
						<a href={resolve('/forgot-password')} class="forgot-link">Forgot password?</a>
					</div>
				</div>

				<button
					type="submit"
					disabled={busy}
					aria-busy={busy}
					class="submit-btn staff-btn"
				>
					{#if busy}
						<Spinner class="h-4 w-4 text-white" />
					{:else}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="btn-icon">
							<path fill-rule="evenodd" d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z" clip-rule="evenodd" />
							<path fill-rule="evenodd" d="M6 10a.75.75 0 01.75-.75h9.546l-1.048-.943a.75.75 0 111.004-1.114l2.5 2.25a.75.75 0 010 1.114l-2.5 2.25a.75.75 0 11-1.004-1.114l1.048-.943H6.75A.75.75 0 016 10z" clip-rule="evenodd" />
						</svg>
					{/if}
					Sign in to Staff Portal
				</button>
			</form>

			<div class="portal-switch">
				<div class="switch-divider">
					<span class="switch-divider-text">Not staff?</span>
				</div>
				<a href={resolve('/client/login')} class="switch-link client-switch">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="switch-icon">
						<path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
					</svg>
					Go to Client Portal →
				</a>
			</div>
		</div>
	</div>
</div>

<style>
	.login-root {
		display: flex;
		min-height: 100vh;
		font-family: 'Inter', system-ui, sans-serif;
	}

	/* ---- Left brand panel ---- */
	.brand-panel {
		display: none;
		flex: 1;
		background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%);
		padding: 3rem;
		position: relative;
		overflow: hidden;
	}
	.brand-panel::before {
		content: '';
		position: absolute;
		inset: 0;
		background:
			radial-gradient(ellipse at 20% 80%, rgba(99, 102, 241, 0.3) 0%, transparent 60%),
			radial-gradient(ellipse at 80% 20%, rgba(167, 139, 250, 0.2) 0%, transparent 60%);
	}
	@media (min-width: 900px) {
		.brand-panel { display: flex; align-items: center; }
	}
	.brand-inner {
		position: relative;
		z-index: 1;
	}
	.brand-logo {
		width: 64px;
		height: 64px;
		background: rgba(255, 255, 255, 0.15);
		border: 1px solid rgba(255, 255, 255, 0.25);
		border-radius: 16px;
		display: flex;
		align-items: center;
		justify-content: center;
		backdrop-filter: blur(8px);
		margin-bottom: 1.5rem;
	}
	.brand-logo-icon {
		width: 36px;
		height: 36px;
		color: #fff;
	}
	.brand-title {
		font-size: 2rem;
		font-weight: 800;
		color: #fff;
		letter-spacing: -0.5px;
		margin: 0 0 0.25rem;
	}
	.brand-subtitle {
		font-size: 0.875rem;
		color: rgba(196, 181, 253, 0.9);
		margin: 0 0 3rem;
		text-transform: uppercase;
		letter-spacing: 1.5px;
		font-weight: 600;
	}
	.brand-features {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.brand-feature {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: rgba(224, 231, 255, 0.9);
		font-size: 0.9rem;
	}
	.feature-icon {
		width: 18px;
		height: 18px;
		color: #a5b4fc;
		flex-shrink: 0;
	}

	/* ---- Right form panel ---- */
	.form-panel {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem 1.5rem;
		background: #f8fafc;
	}
	.form-card {
		width: 100%;
		max-width: 420px;
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 16px;
		padding: 2.5rem;
		box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
	}

	/* Role badge */
	.role-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.875rem;
		border-radius: 999px;
		font-size: 0.75rem;
		font-weight: 700;
		letter-spacing: 0.5px;
		text-transform: uppercase;
		margin-bottom: 1.5rem;
	}
	.role-badge.staff {
		background: #ede9fe;
		color: #4f46e5;
		border: 1px solid #c4b5fd;
	}
	.role-icon {
		width: 14px;
		height: 14px;
	}

	.form-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: #0f172a;
		margin: 0 0 0.25rem;
	}
	.form-subtitle {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0 0 1.75rem;
	}

	.error-box {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 8px;
		padding: 0.75rem 1rem;
		font-size: 0.875rem;
		color: #b91c1c;
		margin-bottom: 1.25rem;
	}
	.error-icon {
		width: 16px;
		height: 16px;
		flex-shrink: 0;
		margin-top: 1px;
	}

	.form-body {
		display: flex;
		flex-direction: column;
		gap: 1.125rem;
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}
	.field-label {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #374151;
	}
	.input-wrap {
		position: relative;
	}
	.input-icon {
		position: absolute;
		left: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		width: 16px;
		height: 16px;
		color: #94a3b8;
		pointer-events: none;
	}
	.input-field {
		width: 100%;
		padding: 0.625rem 0.875rem 0.625rem 2.375rem;
		border: 1px solid #cbd5e1;
		border-radius: 8px;
		font-size: 0.875rem;
		color: #0f172a;
		background: #fff;
		box-sizing: border-box;
		transition: border-color 0.15s, box-shadow 0.15s;
		outline: none;
	}
	.input-field:focus {
		border-color: #6366f1;
		box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
	}
	.input-field::placeholder {
		color: #cbd5e1;
	}
	.forgot-wrap {
		text-align: right;
	}
	.forgot-link {
		font-size: 0.75rem;
		font-weight: 600;
		color: #6366f1;
		text-decoration: none;
	}
	.forgot-link:hover { color: #4f46e5; }

	.submit-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.75rem 1.25rem;
		border: none;
		border-radius: 9px;
		font-size: 0.9375rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.15s, box-shadow 0.15s, opacity 0.15s;
		margin-top: 0.5rem;
	}
	.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
	.staff-btn {
		background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
		color: #fff;
		box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);
	}
	.staff-btn:hover:not(:disabled) {
		box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
		background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
	}
	.btn-icon {
		width: 17px;
		height: 17px;
		flex-shrink: 0;
	}

	/* Portal switch */
	.portal-switch {
		margin-top: 1.75rem;
	}
	.switch-divider {
		position: relative;
		display: flex;
		align-items: center;
		margin-bottom: 1rem;
	}
	.switch-divider::before,
	.switch-divider::after {
		content: '';
		flex: 1;
		height: 1px;
		background: #e2e8f0;
	}
	.switch-divider-text {
		padding: 0 0.75rem;
		font-size: 0.75rem;
		color: #94a3b8;
		font-weight: 500;
	}
	.switch-link {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.625rem 1rem;
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 600;
		text-decoration: none;
		transition: background 0.15s, color 0.15s;
		border: 1px solid;
	}
	.client-switch {
		border-color: #bae6fd;
		color: #0369a1;
		background: #f0f9ff;
	}
	.client-switch:hover {
		background: #e0f2fe;
		border-color: #7dd3fc;
	}
	.switch-icon {
		width: 16px;
		height: 16px;
	}
</style>
