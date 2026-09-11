import { test as setup, expect, submitLogin } from './fixtures';
import { ADMIN, ADMIN_STORAGE_STATE } from './constants';

setup('log in as admin', async ({ page }) => {
	await page.goto('/login');
	await submitLogin(page, ADMIN.username, ADMIN.password);
	await expect(page).toHaveURL(/\/dashboard$/);
	await page.context().storageState({ path: ADMIN_STORAGE_STATE });
});
