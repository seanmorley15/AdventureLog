import type { Locator, Page } from '@playwright/test';
import { test, expect } from '../fixtures';
import { pickPointOnMap } from '../support/locations';
import { openNewCollection, planSection, typeDate } from '../support/trip';

/** Choose a zone in the TimezoneSelector labelled `label`. */
async function chooseZone(page: Page, scope: Locator, label: string, zone: string) {
	await scope.getByRole('button', { name: label }).click();
	await page.getByPlaceholder('Search timezone').fill(zone);
	await page.getByRole('option', { name: zone, exact: true }).click();
}

// #653, #801: plan a trip abroad without picking the destination's zone for every entry.
test.describe('trip time zone', () => {
	// The planner's own browser is in New York; the trip is in Tokyo.
	test.use({ timezoneId: 'America/New_York' });

	test('new stays in a trip start in the time zone chosen for the trip', async ({ page }) => {
		const name = `Tokyo ${Date.now().toString(36)}`;
		const form = await openNewCollection(page);
		await form.getByRole('textbox', { name: 'Name*' }).fill(name);
		await form.getByRole('button', { name: 'Trip' }).click();
		await typeDate(form.getByRole('textbox', { name: 'Start Date' }), '04/01/2027');
		await typeDate(form.getByRole('textbox', { name: 'End Date' }), '04/03/2027');
		// The trip's zone starts as this browser's.
		const tripZone = form.getByRole('button', { name: 'Trip time zone' });
		await expect(tripZone).toContainText('America/New_York');
		await chooseZone(page, form, 'Trip time zone', 'Asia/Tokyo');
		await expect(tripZone).toContainText('Asia/Tokyo');
		await form.getByRole('button', { name: 'Save', exact: true }).click();
		await expect(form).toBeHidden();

		await page.getByRole('link', { name }).first().click();
		const day1 = planSection(page, 1);
		await day1.getByRole('button', { name: 'Add', exact: true }).click();
		await day1.getByRole('menuitem', { name: 'Lodging', exact: true }).click();
		const stay = page.getByRole('dialog').filter({ hasText: 'New Lodging' });
		await pickPointOnMap(page, stay);
		await stay.getByRole('button', { name: 'Continue' }).click();
		// The zone picker shows for timed stays.
		await stay.getByText('All Day', { exact: true }).click();
		await expect(stay.getByRole('button', { name: 'Timezone' })).toContainText('Asia/Tokyo');
	});
});
