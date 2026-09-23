import { defineConfig, devices } from '@playwright/test';
import { ADMIN_STORAGE_STATE } from './tests/e2e/constants';

// Point PLAYWRIGHT_BASE_URL at a running AdventureLog instance. The default matches
// the e2e compose stack (docker/docker-compose.e2e.yml, started with `pnpm e2e:up`).
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:8017';

export default defineConfig({
	testDir: './tests/e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	workers: process.env.CI ? 1 : undefined,
	timeout: 45_000,
	reporter: process.env.CI
		? [['list'], ['github'], ['html', { open: 'never' }]]
		: [['list'], ['html', { open: 'on-failure' }]],
	use: {
		baseURL,
		locale: 'en-US',
		timezoneId: 'UTC',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure'
	},
	projects: [
		{ name: 'setup', testMatch: /.*\.setup\.ts/ },
		{
			name: 'chromium',
			use: {
				...devices['Desktop Chrome'],
				storageState: ADMIN_STORAGE_STATE,
				// The location modal mounts a MapLibre map; recent Chromium builds refuse
				// software WebGL in headless mode without these.
				launchOptions: {
					args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
				}
			},
			dependencies: ['setup']
		}
	]
});
