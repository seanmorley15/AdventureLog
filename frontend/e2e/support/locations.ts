import { expect, type Locator, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';

export const SAMPLE_IMAGE = fileURLToPath(new URL('../assets/sample.png', import.meta.url));

export type NewLocation = {
	name: string;
	category: string;
	tags?: string[];
	description?: string;
	/** Start (and optional end) of one visit, typed the way a user types it: MM/DD/YYYY. */
	visit?: { start: string; notes?: string };
	image?: string;
};

/** Open the "New Location" wizard from the locations page. */
export async function openNewLocation(page: Page): Promise<Locator> {
	await page.goto('/locations');
	// The floating "+" menu is on the page whether or not there are locations. Its button has
	// no accessible name (icon only), so it is found by position.
	const floating = page.locator('div.fixed.bottom-6.right-6');
	await floating.locator('[role="button"]').click();
	await floating.getByRole('button', { name: 'Location' }).click();
	const dialog = page.getByRole('dialog', { name: 'New Location' });
	await expect(dialog).toBeVisible();
	return dialog;
}

/** Pick an existing category, or create it the first time it is needed. */
async function chooseCategory(dialog: Locator, name: string) {
	await dialog.getByRole('button', { name: 'Category *' }).click();
	const existing = dialog.getByRole('button', { name }).first();
	if (await existing.isVisible().catch(() => false)) {
		await existing.click();
	} else {
		await dialog.getByRole('textbox', { name: 'Category Name' }).fill(name);
		await dialog.getByRole('button', { name: 'Add', exact: true }).first().click();
	}
	await expect(dialog.getByRole('button', { name: /Category/ }).first()).toContainText(name);
}

/**
 * Click the middle of the map to choose a point (geocoding is stubbed, see network.ts). Works
 * for every wizard with a map; it returns once the point has been looked up, because the
 * place's name and address are filled in from that answer.
 */
export async function pickPointOnMap(page: Page, dialog: Locator) {
	const map = dialog.getByRole('region', { name: 'Map' });
	await map.scrollIntoViewIfNeeded();
	const box = (await map.boundingBox())!;
	const looked = page.waitForResponse((r) => r.url().includes('/api/places/reverse'));
	await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
	await looked;
}

/**
 * Drive the whole wizard (Quick Start, Details, Media, Visits) the way a person would, and
 * return once the dialog has closed. Starts from an open wizard, see openNewLocation().
 */
export async function createLocationThroughWizard(page: Page, dialog: Locator, data: NewLocation) {
	// Quick Start: skip the search and go to the details form.
	await dialog.getByRole('button', { name: 'Continue' }).click();

	// Details. Pick the point first: choosing a place on the map fills in the place's own
	// name, which would replace a name typed before it.
	await pickPointOnMap(page, dialog);
	await dialog.getByRole('textbox', { name: 'Name *' }).fill(data.name);
	await chooseCategory(dialog, data.category);
	if (data.description) {
		await dialog.getByRole('textbox', { name: 'Description' }).fill(data.description);
	}
	for (const tag of data.tags ?? []) {
		const input = dialog.getByRole('textbox', { name: 'Add a tag' });
		await input.fill(tag);
		await input.press('Enter');
	}
	// Continuing from Details saves the location.
	const saved = page.waitForResponse(
		(r) => r.url().includes('/api/locations') && r.request().method() === 'POST' && r.ok()
	);
	await dialog.getByRole('button', { name: 'Continue' }).click();
	await saved;

	// Media
	await expect(dialog.getByRole('heading', { name: 'Image Management' })).toBeVisible();
	if (data.image) {
		await dialog.locator('input[type="file"]').first().setInputFiles(data.image);
		await expect(dialog.getByRole('img', { name: /./ }).first()).toBeVisible();
	}
	await dialog.getByRole('button', { name: 'Continue' }).click();

	// Visits
	await expect(dialog.getByRole('heading', { name: 'Add Visit' })).toBeVisible();
	if (data.visit) {
		const start = dialog.getByRole('textbox', { name: 'Start Date' });
		await start.fill(data.visit.start);
		// The date is parsed when the field loses focus, which is what enables "Add Visit".
		await start.press('Tab');
		if (data.visit.notes)
			await dialog.getByRole('textbox', { name: 'Notes' }).fill(data.visit.notes);
		await dialog.getByRole('button', { name: 'Add Visit' }).last().click();
		await expect(dialog.getByRole('heading', { name: 'Visits (1)' })).toBeVisible();
	}
	await dialog.getByRole('button', { name: 'Done' }).click();
	await expect(dialog).toBeHidden();
}
