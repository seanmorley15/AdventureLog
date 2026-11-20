import type { Page } from '@playwright/test';
import { test, expect } from '../fixtures';

/** POST to the API from the signed-in page, the way the app's own components do. */
async function api(page: Page, path: string, body: unknown) {
	const result = await page.evaluate(
		async ({ path, body }) => {
			const res = await fetch(path, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			return { ok: res.ok, body: await res.json() };
		},
		{ path, body }
	);
	expect(result.ok, JSON.stringify(result.body)).toBe(true);
	return result.body;
}

// #1234: narrow a collection full of suggestions to the best-rated places.
test('the minimum rating filter hides lower-rated and unrated places', async ({ page }) => {
	await page.goto('/collections');
	const suffix = Date.now().toString(36);
	const folder = await api(page, '/api/collections/', { name: `Rated ${suffix}` });
	for (const [name, rating] of [
		['Three Star Cafe', 3],
		['Four Star Museum', 4],
		['Five Star Viewpoint', 5],
		['Unrated Bench', null]
	] as const) {
		await api(page, '/api/locations/', { name, rating, collections: [folder.id] });
	}

	await page.goto(`/collections/${folder.id}?view=all`);
	await expect(page.getByText('Three Star Cafe').first()).toBeVisible();

	await page.getByRole('button', { name: 'Show Filters' }).click();
	await page.getByRole('button', { name: '4★+' }).click();

	await expect(page.getByText('Four Star Museum').first()).toBeVisible();
	await expect(page.getByText('Five Star Viewpoint').first()).toBeVisible();
	await expect(page.getByText('Three Star Cafe')).toHaveCount(0);
	await expect(page.getByText('Unrated Bench')).toHaveCount(0);

	await page.getByRole('button', { name: 'Reset', exact: true }).click();
	await expect(page.getByText('Unrated Bench').first()).toBeVisible();
});
