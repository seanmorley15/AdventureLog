import { test, expect } from '../fixtures';

// Regression: between about 1280 and 1327px the navbar's "..." settings button (language,
// theme and About) used to be laid out past the right edge of the window and could not be
// reached. 1280px is a very common laptop width.
test.describe('navbar at 1280px', () => {
	test.use({ viewport: { width: 1280, height: 800 } });

	test('the settings menu button is inside the window', async ({ page }) => {
		await page.goto('/dashboard');
		const button = page
			.locator('div.dropdown', { has: page.locator('button', { hasText: 'About AdventureLog' }) })
			.locator('> button[aria-haspopup="menu"]');
		await expect(button).toBeVisible();

		const box = (await button.boundingBox())!;
		const viewportWidth = page.viewportSize()!.width;
		expect(box.x + box.width, 'right edge of the settings button').toBeLessThanOrEqual(
			viewportWidth
		);
	});
});
