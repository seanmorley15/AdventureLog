import { test, expect } from '../fixtures';

// BUG: with a viewport between about 1280 and 1327px wide, the navbar's "..." settings button
// (language, theme and About) is laid out past the right edge of the window. The page does not
// scroll horizontally, so it cannot be reached. At 1280px it is 46px outside the window; from
// 1328px up, and below 1280px (where the navbar is compact), it fits. 1280px is a very common
// laptop width, and Playwright's own default desktop viewport.
//
// `test.fail()` keeps the suite green while that is true and turns red when it is fixed:
// delete the line then.
test.describe('navbar at 1280px', () => {
	test.use({ viewport: { width: 1280, height: 800 } });
	test.fail();

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
