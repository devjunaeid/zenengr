import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({
				fallback: 'index.html',
				pages: 'build',
				assets: 'build',
				precompress: false,
				strict: false
			})
		})
	],
	server: {
		// Dockerized dev: bind-mount filesystem misses native fs events, so poll.
		watch: {
			usePolling: true,
			interval: 300,
			awaitWriteFinish: {
				stabilityThreshold: 100,
				pollInterval: 100
			}
		},
		hmr: {
			// HMR websocket must reach the host browser through the published port.
			host: 'localhost',
			clientPort: 5173
		}
	}
});
