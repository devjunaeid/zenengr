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

<svelte:head><title>Client Sign In — ZenEngr</title></svelte:head>

<div class="login-root">
	<!-- Left brand panel -->
	<div class="brand-panel">
		<div class="brand-inner">
			<div class="brand-logo">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="brand-logo-icon">
					<path d="M4.5 6.375a4.125 4.125 0 118.25 0 4.125 4.125 0 01-8.25 0zM14.25 8.625a3.375 3.375 0 116.75 0 3.375 3.375 0 01-6.75 0zM1.5 19.125a7.125 7.125 0 0114.25 0v.003l-.001.119a.75.75 0 01-.363.63 13.067 13.067 0 01-6.761 1.873c-2.472 0-4.786-.684-6.76-1.873a.75.75 0 01-.364-.63l-.001-.122zM17.25 19.128l-.001.144a2.25 2.25 0 01-.233.96 10.088 10.088 0 005.06-1.01.75.75 0 00.42-.643 4.875 4.875 0 00-6.957-4.611 8.586 8.586 0 011.71 5.157v.003z" />
				</svg>
			</div>
			<h2 class="brand-title">Client Portal</h2>
			<p class="brand-subtitle">ZenEngr</p>

			<div class="brand-features">
				<div class="brand-feature">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="feature-icon">
						<path d="M3 4a2 2 0 00-2 2v1.161l8.441 4.221a1.25 1.25 0 001.118 0L19 7.162V6a2 2 0 00-2-2H3z" />
						<path d="M19 8.839l-7.77 3.885a2.75 2.75 0 01-2.46 0L1 8.839V14a2 2 0 002 2h14a2 2 0 002-2V8.839z" />
					</svg>
					<span>View & download invoices</span>
				</div>
				<div class="brand-feature">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="feature-icon">
						<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z" clip-rule="evenodd" />
					</svg>
					<span>Track project progress</span>
				</div>
				<div class="brand-feature">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="feature-icon">
						<path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" />
					</svg>
					<span>Manage your profile</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Right form panel -->
	<div class="form-panel">
		<div class="form-card">
			<!-- Role badge -->
			<div class="role-badge client">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="role-icon">
					<path d="M4.5 6.375a4.125 4.125 0 118.25 0 4.125 4.125 0 01-8.25 0zM14.25 8.625a3.375 3.375 0 116.75 0 3.375 3.375 0 01-6.75 0zM1.5 19.125a7.125 7.125 0 0114.25 0v.003l-.001.119a.75.75 0 01-.363.63 13.067 13.067 0 01-6.761 1.873c-2.472 0-4.786-.684-6.76-1.873a.75.75 0 01-.364-.63l-.001-.122zM17.25 19.128l-.001.144a2.25 2.25 0 01-.233.96 10.088 10.088 0 005.06-1.01.75.75 0 00.42-.643 4.875 4.875 0 00-6.957-4.611 8.586 8.586 0 011.71 5.157v.003z" />
				</svg>
				Client Portal
			</div>

			<h1 class="form-title">Welcome back</h1>
			<p class="form-subtitle">Sign in to view your projects and invoices.</p>

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
							placeholder="you@example.com"
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
						<a href={resolve('/client/forgot-password')} class="forgot-link">Forgot password?</a>
					</div>
				</div>

				<button
					type="submit"
					disabled={busy}
					aria-busy={busy}
					class="submit-btn client-btn"
				>
					{#if busy}
						<Spinner class="h-4 w-4 text-white" />
					{:else}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="btn-icon">
							<path fill-rule="evenodd" d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z" clip-rule="evenodd" />
							<path fill-rule="evenodd" d="M6 10a.75.75 0 01.75-.75h9.546l-1.048-.943a.75.75 0 111.004-1.114l2.5 2.25a.75.75 0 010 1.114l-2.5 2.25a.75.75 0 11-1.004-1.114l1.048-.943H6.75A.75.75 0 016 10z" clip-rule="evenodd" />
						</svg>
					{/if}
					Sign in to Client Portal
				</button>
			</form>

			<div class="portal-switch">
				<div class="switch-divider">
					<span class="switch-divider-text">Are you staff?</span>
				</div>
				<a href={resolve('/login')} class="switch-link staff-switch">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="switch-icon">
						<path fill-rule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 00.374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.39-.223-2.73-.635-3.985a.75.75 0 00-.722-.516l-.143.001c-2.996 0-5.717-1.17-7.734-3.08z" clip-rule="evenodd" />
					</svg>
					Go to Staff Portal →
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
		background: linear-gradient(135deg, #0c4a6e 0%, #0369a1 40%, #0ea5e9 100%);
		padding: 3rem;
		position: relative;
		overflow: hidden;
	}
	.brand-panel::before {
		content: '';
		position: absolute;
		inset: 0;
		background:
			radial-gradient(ellipse at 20% 80%, rgba(14, 165, 233, 0.3) 0%, transparent 60%),
			radial-gradient(ellipse at 80% 20%, rgba(56, 189, 248, 0.2) 0%, transparent 60%);
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
		color: rgba(186, 230, 253, 0.9);
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
		color: rgba(224, 242, 254, 0.9);
		font-size: 0.9rem;
	}
	.feature-icon {
		width: 18px;
		height: 18px;
		color: #7dd3fc;
		flex-shrink: 0;
	}

	/* ---- Right form panel ---- */
	.form-panel {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem 1.5rem;
		background: #f0f9ff;
	}
	.form-card {
		width: 100%;
		max-width: 420px;
		background: #fff;
		border: 1px solid #bae6fd;
		border-radius: 16px;
		padding: 2.5rem;
		box-shadow: 0 4px 24px rgba(3, 105, 161, 0.08);
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
	.role-badge.client {
		background: #e0f2fe;
		color: #0369a1;
		border: 1px solid #7dd3fc;
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
		border: 1px solid #bae6fd;
		border-radius: 8px;
		font-size: 0.875rem;
		color: #0f172a;
		background: #fff;
		box-sizing: border-box;
		transition: border-color 0.15s, box-shadow 0.15s;
		outline: none;
	}
	.input-field:focus {
		border-color: #0ea5e9;
		box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.12);
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
		color: #0369a1;
		text-decoration: none;
	}
	.forgot-link:hover { color: #0284c7; }

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
	.client-btn {
		background: linear-gradient(135deg, #0369a1 0%, #0ea5e9 100%);
		color: #fff;
		box-shadow: 0 4px 12px rgba(3, 105, 161, 0.35);
	}
	.client-btn:hover:not(:disabled) {
		box-shadow: 0 6px 20px rgba(3, 105, 161, 0.5);
		background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
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
	.staff-switch {
		border-color: #c4b5fd;
		color: #4f46e5;
		background: #ede9fe;
	}
	.staff-switch:hover {
		background: #ddd6fe;
		border-color: #a5b4fc;
	}
	.switch-icon {
		width: 16px;
		height: 16px;
	}
</style>
