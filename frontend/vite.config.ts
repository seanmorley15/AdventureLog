import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import adapterNode from '@sveltejs/adapter-node';
import adapterVercel from '@sveltejs/adapter-vercel';

// vite.config.js
import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import Icons from 'unplugin-icons/vite';
import { playwright } from '@vitest/browser-playwright';

let adapter;

if (process.env.VERCEL) {
	adapter = adapterVercel;
} else {
	adapter = adapterNode;
}

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			// Consult https://kit.svelte.dev/docs/integrations#preprocessors
			// for more information about preprocessors
			preprocess: vitePreprocess(),

			// adapter-auto only supports some environments, see https://kit.svelte.dev/docs/adapter-auto for a list.
			// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
			// See https://kit.svelte.dev/docs/adapters for more information about adapters.
			adapter: adapter()
		}),
		Icons({ compiler: 'svelte' })
	],
	ssr: {
		// LayerChart ships Svelte source. Vite must compile it during server render.
		noExternal: ['layerchart']
	},
	test: {
		projects: [
			{
				extends: true,
				test: {
					name: 'unit',
					environment: 'node',
					include: ['src/**/*.test.ts'],
					exclude: ['src/**/*.svelte.test.ts'],
					env: { TZ: 'UTC' }
				}
			},
			{
				extends: true,
				test: {
					name: 'component',
					include: ['src/**/*.svelte.test.ts'],
					browser: {
						enabled: true,
						headless: true,
						provider: playwright(),
						instances: [{ browser: 'chromium' }]
					}
				}
			}
		],
		coverage: {
			provider: 'v8',
			include: ['src/lib/**/*.ts'],
			exclude: ['src/lib/api/schema.d.ts', 'src/**/*.test.ts', 'src/lib/test-utils/**']
		}
	}
});
