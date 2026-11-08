import { test, expect } from '../fixtures';
import { logIn, newCredentials, signUp } from '../support/accounts';

// These start signed out. (Other specs start signed in as the worker's account.)
test.use({ storageState: { cookies: [], origins: [] } });

async function logOut(page: import('@playwright/test').Page) {
	await page.locator('div[role="group"] [role="button"]').first().click();
	await page.getByRole('button', { name: 'Logout' }).click();
	// Logging out lands on the public home page; the proof that the session is gone is below.
	await expect(page).not.toHaveURL(/\/dashboard/);
	await page.goto('/locations');
	await expect(page).toHaveURL(/\/login/);
}

test.describe('signed out', () => {
	test('protected pages send you to the login page', async ({ page }) => {
		for (const path of ['/locations', '/collections', '/settings', '/calendar']) {
			await page.goto(path);
			await expect(page, `${path} should require a login`).toHaveURL(/\/login/);
		}
	});

	// The 400 for the wrong password is logged by Chrome as a console error, so this test is
	// allowed to see one.
	test.describe(() => {
		test.use({ allowBrokenUI: true });
		test('a wrong password shows an error and stays on the login page', async ({
			page,
			account
		}) => {
			await page.goto('/login');
			await page.locator('input[name="username"]').fill(account.username);
			await page.locator('input[name="password"]').fill('not-the-password-123');
			await page.locator('form button[type="submit"]').click();

			await expect(page.getByText('Invalid credentials')).toBeVisible();
			await expect(page).toHaveURL(/\/login/);
		});
	});
});

test.describe('signup', () => {
	test('creates an account, signs you in and greets you by name', async ({ page }) => {
		const creds = newCredentials('signup');
		await signUp(page, creds);
		await expect(page).toHaveURL(/\/dashboard/);
		await expect(
			page.getByRole('heading', { name: /Good (morning|afternoon|evening)/ })
		).toContainText(creds.firstName);
	});

	// The server's 400 for the mismatch is logged by Chrome as a console error.
	test.describe(() => {
		test.use({ allowBrokenUI: true });
		test('refuses mismatched passwords', async ({ page }) => {
			const creds = newCredentials('mismatch');
			await page.goto('/signup');
			await page.locator('input[name="username"]').fill(creds.username);
			await page.locator('input[name="email"]').fill(creds.email);
			await page.locator('input[name="first_name"]').fill(creds.firstName);
			await page.locator('input[name="last_name"]').fill(creds.lastName);
			await page.locator('input[name="password1"]').fill(creds.password);
			await page.locator('input[name="password2"]').fill(`${creds.password}-different`);
			const terms = page.locator('input[name="accept_terms"]');
			if (await terms.count()) await terms.check();
			await page.locator('form button[type="submit"]').click();

			await expect(page).toHaveURL(/\/signup/);
			await expect(page.locator('.alert-error')).toContainText(/match/i);
		});
	});
});

test.describe('session', () => {
	test('logs in, survives a reload, logs out and is locked out again', async ({ page }) => {
		const creds = newCredentials('session');
		await signUp(page, creds);
		await logOut(page);

		await logIn(page, creds);
		await expect(page).toHaveURL(/\/dashboard/);
		await page.reload();
		await expect(page).toHaveURL(/\/dashboard/);

		await logOut(page);
		await page.goto('/locations');
		await expect(page).toHaveURL(/\/login/);
	});
});
