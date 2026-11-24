import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:8015';
const isCI = !!process.env.CI;

export default defineConfig({
	testDir: 'e2e',
	testMatch: '**/*.spec.ts',
	outputDir: 'test-results',
	fullyParallel: true,
	forbidOnly: isCI,
	retries: isCI ? 2 : 0,
	workers: isCI ? 2 : undefined,
	timeout: 60_000,
	expect: { timeout: 10_000 },
	// `blob` lets CI shards be merged into one HTML report afterwards.
	reporter: isCI
		? [['blob'], ['list']]
		: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
	use: {
		baseURL,
		// A wrong locator should fail in seconds, not after the whole test timeout.
		actionTimeout: 15_000,
		navigationTimeout: 30_000,
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
		video: 'retain-on-failure',
		// The suite asserts on English copy; pin it so a developer's browser locale cannot leak in.
		locale: 'en-US',
		// A real zone, not UTC: a browser that reports "UTC" currently cannot add a visit
		// (see specs/timezone-utc.spec.ts), so the journeys run as a typical user would.
		timezoneId: 'America/New_York'
	},
	projects: [
		{
			name: 'chromium-desktop',
			// Not Playwright's default 1280 wide: between 1280 and about 1327px the navbar's
			// settings menu is pushed off-screen (see specs/navbar-width.spec.ts).
			use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } }
		},
		{
			// Only specs tagged @mobile run here, so responsive layouts are covered without
			// doubling the CI time of the whole suite.
			name: 'chromium-mobile',
			use: { ...devices['Pixel 7'] },
			grep: /@mobile/
		}
	]
});
