/// <reference types="@sveltejs/kit" />
import { build, files, version } from '$service-worker';

// Unique cache key keyed by release version
const CACHE = `cache-zenengr-${version}`;

// App shell and static assets to pre-cache on install
const ASSETS = [...build, ...files];

self.addEventListener('install', (event) => {
	async function addFilesToCache() {
		const cache = await caches.open(CACHE);
		// Precache assets. Use Promise.allSettled so a single missing optional file doesn't block install.
		await Promise.allSettled(ASSETS.map((asset) => cache.add(asset)));
	}

	event.waitUntil(addFilesToCache().then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
	async function deleteOldCaches() {
		for (const key of await caches.keys()) {
			if (key !== CACHE && key.startsWith('cache-zenengr-')) {
				await caches.delete(key);
			}
		}
	}

	event.waitUntil(deleteOldCaches().then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
	const { request } = event;

	// Only handle GET requests
	if (request.method !== 'GET') return;

	const url = new URL(request.url);

	// Completely ignore API requests, WebSockets, or cross-origin calls
	if (
		url.pathname.startsWith('/api/') ||
		url.pathname.startsWith('/ws/') ||
		url.protocol.startsWith('ws') ||
		url.origin !== location.origin
	) {
		return;
	}

	// Immutable build artifacts (/_app/immutable/*) and known static assets: Cache-First
	if (url.pathname.startsWith('/_app/') || ASSETS.includes(url.pathname)) {
		event.respondWith(
			caches.match(request).then(async (cachedResponse) => {
				if (cachedResponse) return cachedResponse;
				try {
					const networkResponse = await fetch(request);
					if (networkResponse.ok) {
						const cache = await caches.open(CACHE);
						cache.put(request, networkResponse.clone());
					}
					return networkResponse;
				} catch {
					return cachedResponse || new Response('Asset unavailable offline', { status: 503 });
				}
			})
		);
		return;
	}

	// Navigation requests: Network-first, falling back to cached app shell
	if (request.mode === 'navigate') {
		event.respondWith(
			fetch(request).catch(async () => {
				const cache = await caches.open(CACHE);
				// In SPA mode, serve root / or index.html or matched path
				const cached =
					(await cache.match(request)) ||
					(await cache.match('/')) ||
					(await cache.match('/index.html'));
				if (cached) return cached;
				return new Response('You are offline and this page has not yet been cached.', {
					status: 503,
					headers: { 'Content-Type': 'text/plain; charset=utf-8' }
				});
			})
		);
		return;
	}

	// Other same-origin GET requests: Network-first with cache fallback
	event.respondWith(
		fetch(request).catch(async () => {
			const cached = await caches.match(request);
			if (cached) return cached;
			return new Response('Offline', { status: 503 });
		})
	);
});
