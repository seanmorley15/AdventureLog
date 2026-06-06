// vite.config.js
import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import Icons from 'unplugin-icons/vite';

const backendTarget = process.env.PUBLIC_SERVER_URL ?? 'http://127.0.0.1:8000';
const useDevProxy = !process.env.CI && process.env.VITEST !== 'true';

export default defineConfig({
	plugins: [
		sveltekit(),
		Icons({
			compiler: 'svelte'
		})
	],
	server: useDevProxy
		? {
				proxy: {
					'/api': { target: backendTarget, changeOrigin: true },
					'/auth': { target: backendTarget, changeOrigin: true }
				}
			}
		: undefined
});
