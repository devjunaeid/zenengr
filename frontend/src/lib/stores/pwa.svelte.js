import { browser } from '$app/environment';

let isOnline = $state(true);
let isStandalone = $state(false);
let canInstall = $state(false);
/** @type {any} */
let deferredPrompt = null;
let initialized = false;

export const pwa = {
	get isOnline() {
		return isOnline;
	},
	get isStandalone() {
		return isStandalone;
	},
	get canInstall() {
		return canInstall;
	},

	/**
	 * Prompt the user with the native browser install dialog if available.
	 * @returns {Promise<'accepted'|'dismissed'|'unavailable'>}
	 */
	async promptInstall() {
		if (!deferredPrompt) return 'unavailable';
		try {
			deferredPrompt.prompt();
			const choice = await deferredPrompt.userChoice;
			deferredPrompt = null;
			canInstall = false;
			return choice?.outcome || 'dismissed';
		} catch (err) {
			console.warn('PWA install prompt error:', err);
			deferredPrompt = null;
			canInstall = false;
			return 'dismissed';
		}
	},

	/**
	 * Initialize listeners for network status, installability, and register service worker.
	 */
	init() {
		if (!browser || initialized) return;
		initialized = true;

		// Network status
		isOnline = navigator.onLine;
		window.addEventListener('online', () => {
			isOnline = true;
		});
		window.addEventListener('offline', () => {
			isOnline = false;
		});

		// Standalone mode detection (desktop PWA or iOS home screen)
		const checkStandalone = () => {
			const displayModeStandalone = window.matchMedia('(display-mode: standalone)').matches;
			/** @type {any} */
			const nav = navigator;
			return displayModeStandalone || !!nav.standalone;
		};
		isStandalone = checkStandalone();

		// Browser install prompt interception
		window.addEventListener('beforeinstallprompt', (e) => {
			// Prevent the mini-infobar from appearing on mobile automatically
			e.preventDefault();
			deferredPrompt = e;
			canInstall = true;
		});

		window.addEventListener('appinstalled', () => {
			deferredPrompt = null;
			canInstall = false;
			isStandalone = true;
		});

		// Register Service Worker
		if ('serviceWorker' in navigator) {
			navigator.serviceWorker.register('/service-worker.js').catch((err) => {
				console.warn('Service worker registration failed:', err);
			});
		}
	}
};
