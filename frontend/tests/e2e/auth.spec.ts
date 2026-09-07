import { test, expect, submitLogin } from './fixtures';
import { ADMIN } from './constants';

// These run logged out, without the admin session the other specs reuse.
test.use({ storageState: { cookies: [], origins: [] } });

test.describe('login', () => {
	test('logs in with valid credentials', async ({ page }) => {
		await page.goto('/login');
		await submitLogin(page, ADMIN.username, ADMIN.password);

		await expect(page).toHaveURL(/\/dashboard$/);
	});

	test('rejects a wrong password', async ({ page }) => {
		await page.goto('/login');
		await submitLogin(page, ADMIN.username, 'not-the-password');

		await expect(page.locator('.alert-error')).toBeVisible();
		await expect(page).toHaveURL(/\/login$/);
	});

	test('sends a logged-out visitor from /locations to /login', async ({ page }) => {
		await page.goto('/locations');
		await expect(page).toHaveURL(/\/login$/);
	});
});
