import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test as base, expect } from '@playwright/test';
import { newCredentials, signUp, type Credentials } from './support/accounts';
import { watchForBrokenUI } from './support/guard';
import { stubExternalNetwork } from './support/network';
import { rawTranslationKeys } from './support/translations';

type WorkerFixtures = {
	/** A real account for this worker, created through the signup page once and reused. */
	account: Credentials & { storageState: string };
};

type TestFixtures = {
	/** Fails the test when the UI throws, logs console errors, or the API answers 5xx. */
	brokenUIGuard: void;
	/** Opt out of the guard for a test that provokes errors on purpose. */
	allowBrokenUI: boolean;
};

export const test = base.extend<TestFixtures, WorkerFixtures>({
	account: [
		async ({ browser }, use, workerInfo) => {
			const baseURL = workerInfo.project.use.baseURL!;
			const creds = newCredentials(`w${workerInfo.workerIndex}`);
			const context = await browser.newContext({ baseURL, locale: 'en-US' });
			await stubExternalNetwork(context, baseURL);
			const page = await context.newPage();
			await signUp(page, creds);
			const storageState = join(mkdtempSync(join(tmpdir(), 'adventurelog-e2e-')), 'state.json');
			await context.storageState({ path: storageState });
			await context.close();
			await use({ ...creds, storageState });
		},
		{ scope: 'worker' }
	],

	// Tests start signed in as the worker's account. Journeys that need a brand-new user
	// override this with `test.use({ storageState: { cookies: [], origins: [] } })`.
	storageState: async ({ account }, use) => {
		await use(account.storageState);
	},

	context: async ({ context, baseURL }, use) => {
		await stubExternalNetwork(context, baseURL!);
		await use(context);
	},

	allowBrokenUI: [false, { option: true }],

	brokenUIGuard: [
		async ({ page, allowBrokenUI }, use) => {
			const guard = watchForBrokenUI(page);
			await use();
			if (!allowBrokenUI) {
				expect(guard.issues(), 'the UI reported errors while this test ran').toEqual([]);
				if (!page.isClosed() && page.url().startsWith('http')) {
					expect(
						await rawTranslationKeys(page),
						'visible text that is an untranslated key (missing from locales/en.json)'
					).toEqual([]);
				}
			}
		},
		{ auto: true }
	]
});

export { expect };
