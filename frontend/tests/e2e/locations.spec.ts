import { test, expect } from './fixtures';

test.describe('locations', () => {
	test('creates a location from the details step', async ({ page, api }) => {
		const suffix = `${Date.now()}-${test.info().workerIndex}`;
		const name = `E2E Location ${suffix}`;
		const category = await api.createCategory(`E2E Category ${suffix}`);

		await page.goto('/locations');
		await page.getByRole('button', { name: 'Create New' }).click();
		await page.getByRole('button', { name: 'Location', exact: true }).click();

		const modal = page.locator('dialog[open]');
		await expect(modal.getByRole('heading', { name: 'New Location' })).toBeVisible();

		// Quick Start is a map; the details step is enough to save a location.
		await modal.getByRole('button', { name: 'Details', exact: true }).click();
		await modal.getByLabel(/^Name/).fill(name);
		await modal.getByRole('button', { name: 'Select Category' }).click();
		await modal.getByRole('option', { name: category.display_name }).click();

		const saved = page.waitForResponse(
			(res) => res.request().method() === 'POST' && new URL(res.url()).pathname === '/api/locations'
		);
		await modal.getByRole('button', { name: 'Continue' }).click();
		const response = await saved;
		expect(response.status()).toBe(201);
		api.trackLocation((await response.json()).id);

		await modal.getByRole('button', { name: 'Close', exact: true }).first().click();
		await expect(modal).toBeHidden();
		await expect(
			page.locator('[aria-label="location-card"]').filter({ hasText: name })
		).toBeVisible();
	});
});
