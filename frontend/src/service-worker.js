/// <reference types="@sveltejs/kit" />
import { build, files, version } from '$service-worker';

// Unique cache key keyed by release version
const CACHE = `cache-zenengr-${version}`;

// Known build artifacts and static assets
const ASSETS = new Set([...build, ...files]);
// Core shell to precache on install (avoid mass network flooding on initial visit)
const CORE_PRECACHE = ['/', '/index.html'];

self.addEventListener('install', (event) => {
	async function addFilesToCache() {
		const cache = await caches.open(CACHE);
		await Promise.allSettled(CORE_PRECACHE.map((asset) => cache.add(asset)));
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

	// In development, do not intercept fetch requests to avoid interfering with Vite HMR
	if (import.meta.env.DEV) return;

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
	if (url.pathname.startsWith('/_app/') || ASSETS.has(url.pathname)) {
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
				return new Response(
					`<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Offline — ZenEngr</title><style>body{font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f8fafc;color:#1e293b;padding:1rem}.card{background:#fff;padding:2rem;border-radius:1rem;box-shadow:0 10px 15px -3px rgb(0 0 0/0.05);max-width:24rem;text-align:center;border:1px solid #e2e8f0}h1{font-size:1.25rem;font-weight:700;margin:0 0 .5rem}p{font-size:.875rem;color:#64748b;margin:0 0 1.5rem;line-height:1.5}button{background:#4f46e5;color:#fff;border:none;padding:.625rem 1.25rem;font-size:.875rem;font-weight:600;border-radius:.5rem;cursor:pointer;min-height:44px;width:100%}button:hover{background:#4338ca}</style></head><body><div class="card"><h1>You're Offline</h1><p>You appear to be offline and this page has not yet been cached. Check your internet connection and try again.</p><button onclick="window.location.reload()">Try Again</button></div></body></html>`,
					{
						status: 503,
						headers: { 'Content-Type': 'text/html; charset=utf-8' }
					}
				);
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
