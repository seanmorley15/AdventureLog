import type { Locator, Page } from '@playwright/test';
import { test, expect } from '../fixtures';
import { newCredentials, signUp } from '../support/accounts';
import { createLocationThroughWizard, openNewLocation, SAMPLE_IMAGE } from '../support/locations';

/** The card's title link for a location, on the list page. */
function titleLink(page: Page, name: string) {
	return page.locator('.card', { hasText: name }).first().locator('a[href^="/locations/"]').first();
}

/** The drawer's description is on Overview; visits (and their notes) are on their own tab. */
async function openVisitsTab(drawer: Locator) {
	await drawer
		.getByRole('tab', { name: /Visits/ })
		.or(drawer.getByRole('button', { name: /^Visits/ }))
		.first()
		.click();
}

test.describe('locations', () => {
	test('create a location through the wizard, find it and open its page', async ({ page }) => {
		const dialog = await openNewLocation(page);
		await createLocationThroughWizard(page, dialog, {
			name: 'Sagrada Familia',
			category: 'Landmark',
			tags: ['gaudi', 'church'],
			description: 'An **unfinished** basilica.',
			visit: { start: '09/14/2027', notes: 'Book tickets early' },
			image: SAMPLE_IMAGE
		});

		// The card shows what was entered.
		const card = page.locator('.card', { hasText: 'Sagrada Familia' }).first();
		await expect(card).toBeVisible();
		await expect(card).toContainText('Landmark');
		await expect(card).toContainText('gaudi');
		await expect(card).toContainText('church');

		// It survives a reload, so it really was saved.
		await page.reload();
		await expect(page.getByText('Sagrada Familia').first()).toBeVisible();

		// Clicking the title opens the details drawer on top of the list (the URL stays put).
		const href = await titleLink(page, 'Sagrada Familia').getAttribute('href');
		await titleLink(page, 'Sagrada Familia').click();
		const drawer = page.getByRole('dialog').filter({ hasText: 'Sagrada Familia' });
		await expect(drawer).toBeVisible();
		await expect(drawer.locator('strong', { hasText: 'unfinished' })).toBeVisible();
		await openVisitsTab(drawer);
		await expect(drawer.getByText('Book tickets early')).toBeVisible();

		// The same location also has a full page of its own.
		await page.goto(href!);
		await expect(page).toHaveURL(/\/locations\/[0-9a-f-]{36}/);
		await expect(page.getByRole('heading', { name: 'Sagrada Familia' }).first()).toBeVisible();
		await expect(page.locator('strong', { hasText: 'unfinished' })).toBeVisible();
	});

	// Regression: the wizard once failed to save a location together with its visits (see
	// commit f381bb98, "create locations with nested visits"). A visit added in the last step
	// must survive a reload.
	test('a visit added while creating a location is saved with it', async ({ page }) => {
		const dialog = await openNewLocation(page);
		await createLocationThroughWizard(page, dialog, {
			name: 'Park Güell',
			category: 'Landmark',
			visit: { start: '09/15/2027', notes: 'Mosaic terrace' }
		});

		await page.reload();
		await titleLink(page, 'Park Güell').click();
		const drawer = page.getByRole('dialog').filter({ hasText: 'Park Güell' });
		await openVisitsTab(drawer);
		await expect(drawer.getByText('Mosaic terrace')).toBeVisible();
	});

	// Regression: the header count and category sidebar used to stay stale until a reload.
	test('the header count and category filters update without a reload', async ({ page }) => {
		const dialog = await openNewLocation(page);
		await createLocationThroughWizard(page, dialog, {
			name: 'Casa Batlló',
			category: 'Modernisme',
			visit: { start: '09/16/2027' }
		});

		await expect(page.getByText('Casa Batlló').first()).toBeVisible();
		await expect(page.getByRole('heading', { name: 'My Locations' }).locator('..')).toContainText(
			/\b[1-9]\d*\s+Locations/
		);
		await expect(page.getByText('No categories found.')).toBeHidden();
	});

	// #1005: someone else's public place can be copied into your own account.
	test("copy someone else's public location into my locations", async ({ page, browser }) => {
		const name = `Shared Viewpoint ${Date.now().toString(36)}`;
		await page.goto('/locations');
		const created = await page.evaluate(async (placeName) => {
			const res = await fetch('/api/locations/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: placeName, is_public: true })
			});
			return { ok: res.ok, body: await res.json() };
		}, name);
		expect(created.ok, JSON.stringify(created.body)).toBe(true);

		const other = await browser.newContext({ storageState: { cookies: [], origins: [] } });
		const otherPage = await other.newPage();
		try {
			await signUp(otherPage, newCredentials('copier'));
			await otherPage.goto(`/locations/${created.body.id}`);
			await expect(otherPage.getByRole('heading', { name }).first()).toBeVisible();
			// Not the owner: no Edit, but a way to keep a copy.
			await expect(otherPage.getByRole('button', { name: 'Edit', exact: true })).toHaveCount(0);
			await otherPage.getByRole('button', { name: 'Copy to my locations' }).click();

			await expect(otherPage).not.toHaveURL(new RegExp(created.body.id));
			await expect(
				otherPage.getByRole('heading', { name: `Copy of ${name}` }).first()
			).toBeVisible();
			await expect(otherPage.getByRole('button', { name: 'Edit', exact: true })).toBeVisible();
		} finally {
			await other.close();
		}
	});
});
