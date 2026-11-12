import { test, expect } from '../fixtures';
import { newCredentials, signUp } from '../support/accounts';
import { openNewCollection } from '../support/trip';

// #1226: a profile can be shown to signed-in users only.
test('a profile can be shown to signed-in users only', async ({ page }) => {
	await page.goto('/settings?tab=profile');
	const signedIn = page.getByRole('radio', { name: /Signed-in users/ });
	await signedIn.check();
	await page.getByRole('button', { name: 'Update', exact: true }).click();
	await expect(page.getByText(/updated/i).first()).toBeVisible();

	await page.reload();
	await expect(page.getByRole('radio', { name: /Signed-in users/ })).toBeChecked();
});

// #621: a collection's story can be shown to everyone signed in, and nobody signed out.
test('a collection shown to everyone signed in opens for other accounts only', async ({
	page,
	browser
}) => {
	const name = `Signed-in Story ${Date.now().toString(36)}`;
	const form = await openNewCollection(page);
	await form.getByRole('textbox', { name: 'Name*' }).fill(name);
	await form.getByRole('button', { name: 'Save & share' }).click();

	const sheet = page.getByRole('dialog', { name: 'Share' });
	await sheet.getByRole('tab', { name: 'Story' }).click();
	await sheet.getByRole('radio', { name: /Everyone signed in/ }).click();
	await expect(sheet.getByRole('radio', { name: /Everyone signed in/ })).toHaveAttribute(
		'aria-checked',
		'true'
	);
	await sheet.getByRole('button', { name: 'Close' }).first().click();
	await page.getByRole('link', { name }).first().click();
	await expect(page).toHaveURL(/\/collections\/[0-9a-f-]{36}/);
	const url = page.url().split('?')[0];

	const other = await browser.newContext({ storageState: { cookies: [], origins: [] } });
	try {
		// Signed out: the API refuses, so the page has no collection to show. (The page itself
		// answers 200 with nothing in it, as it does for any collection you cannot open.)
		const visitor = await other.newPage();
		const api = await visitor.request.get(url.replace('/collections/', '/api/collections/') + '/');
		expect(api.status()).toBe(404);
		await visitor.goto(url);
		await expect(visitor.getByRole('heading', { name })).toHaveCount(0);

		await signUp(visitor, newCredentials('reader'));
		await visitor.goto(url);
		await expect(visitor.getByRole('heading', { name, level: 1 })).toBeVisible();
	} finally {
		await other.close();
	}
});
