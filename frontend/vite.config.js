import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-node';
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
			adapter: adapter()
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
