import { expect, type Locator, type Page } from '@playwright/test';
import { createLocationThroughWizard, pickPointOnMap, type NewLocation } from './locations';

/** Type a date the way a user does (MM/DD/YYYY) and leave the field so it is parsed. */
export async function typeDate(field: Locator, value: string) {
	await field.fill(value);
	await field.press('Tab');
}

/** Create a trip (a collection with dates, which unlocks the day planner) and open it. */
export async function createTrip(
	page: Page,
	trip: { name: string; description?: string; start: string; end: string }
) {
	await page.goto('/collections');
	await page.getByRole('button', { name: 'Create', exact: true }).first().click();
	const dialog = page.getByRole('dialog', { name: 'New Collection' });
	await dialog.getByRole('textbox', { name: 'Name*' }).fill(trip.name);
	if (trip.description) {
		await dialog
			.getByRole('textbox', { name: 'Write your markdown here...' })
			.fill(trip.description);
	}
	await dialog.getByRole('button', { name: 'Trip' }).click();
	await typeDate(dialog.getByRole('textbox', { name: 'Start Date' }), trip.start);
	await typeDate(dialog.getByRole('textbox', { name: 'End Date' }), trip.end);
	await dialog.getByRole('button', { name: 'Save' }).click();
	await expect(dialog).toBeHidden();

	await page.getByRole('link', { name: trip.name }).first().click();
	await expect(page).toHaveURL(/\/collections\/[0-9a-f-]{36}/);
	await expect(page.getByRole('heading', { name: trip.name, level: 1 })).toBeVisible();
}

/** A section of the Plan tab: a day number, or `global` (trip-wide) / `ideas`. */
export function planSection(page: Page, section: number | 'global' | 'ideas') {
	return page.locator(`#plan-section-${section}`);
}

/** Choose an entry from a section's "+" menu. */
async function chooseFromAddMenu(section: Locator, item: string) {
	await section.getByRole('button', { name: 'Add', exact: true }).click();
	await section.getByRole('menuitem', { name: item, exact: true }).click();
}

/**
 * Put places you already have into a section, through "Add existing".
 *
 * One place per visit to the dialog, on purpose. The dialog has a "Done" button for adding
 * several, but it can close itself as soon as the collection refreshes after the first add
 * (see LinkItemsModal.svelte: its `open` attachment reads `collection`, and its cleanup calls
 * `node.close()`), so whether a second add is possible depends on timing. The helper confirms
 * each add by the place showing up in the section, and closes the dialog only if it is open.
 */
export async function addExisting(page: Page, section: Locator, names: string[]) {
	for (const name of names) {
		await chooseFromAddMenu(section, 'Add existing');
		const dialog = page.getByRole('dialog').filter({ hasText: 'Add to' }).last();
		await expect(dialog).toBeVisible();
		const row = dialog
			.locator('div', { has: page.getByText(name, { exact: true }) })
			.filter({ has: page.getByRole('button', { name: 'Add' }) })
			.last();
		await row.getByRole('button', { name: 'Add' }).click();
		await expect(section).toContainText(name);
		await dialog
			.getByRole('button', { name: 'Done' })
			.click({ timeout: 2_000 })
			.catch(() => {});
		await expect(dialog).toBeHidden();
	}
}

export async function addNote(
	page: Page,
	section: Locator,
	note: { name: string; body?: string; link?: string }
) {
	await chooseFromAddMenu(section, 'Note');
	const dialog = page.getByRole('dialog').last();
	await dialog.getByRole('textbox', { name: 'Name*' }).fill(note.name);
	if (note.link) {
		await dialog.getByRole('textbox', { name: 'Links' }).fill(note.link);
		await dialog.getByRole('button', { name: 'Add', exact: true }).click();
	}
	if (note.body) {
		await dialog.getByRole('textbox', { name: 'Write your markdown here...' }).fill(note.body);
	}
	await dialog.getByRole('button', { name: 'Save' }).click();
	await expect(dialog).toBeHidden();
}

export async function addChecklist(
	page: Page,
	section: Locator,
	checklist: { name: string; items: string[] }
) {
	await chooseFromAddMenu(section, 'Checklist');
	const dialog = page.getByRole('dialog').last();
	await dialog.getByRole('textbox', { name: 'Name*' }).fill(checklist.name);
	const input = dialog.getByRole('textbox', { name: 'Add New Item' });
	for (const item of checklist.items) {
		await input.fill(item);
		await dialog.getByRole('button', { name: 'Add', exact: true }).click();
		// Added items are listed in editable fields, so look at the fields' values.
		await expect
			.poll(() =>
				dialog
					.locator('input')
					.evaluateAll((els, v) => els.some((e) => (e as HTMLInputElement).value === v), item)
			)
			.toBe(true);
	}
	await dialog.getByRole('button', { name: 'Save' }).click();
	await expect(dialog).toBeHidden();
}

/** Some dialogs have no accessible name (an a11y gap), so find them by their heading. */
function dialogWithHeading(page: Page, heading: string) {
	return page
		.getByRole('dialog')
		.filter({ has: page.getByRole('heading', { name: heading, level: 1 }) })
		.last();
}

/** The last wizard step of lodging and transportation is Media: nothing to add, so finish. */
async function finishMediaStep(dialog: Locator) {
	await expect(dialog.getByRole('heading', { name: 'Image Management' })).toBeVisible();
	await dialog
		.getByRole('button', { name: /^(Done|Continue)$/ })
		.last()
		.click();
}

/** Create a brand-new place directly in a day (the full location wizard, from the day's menu). */
export async function addNewLocation(page: Page, section: Locator, place: NewLocation) {
	await chooseFromAddMenu(section, 'Location');
	const dialog = page.getByRole('dialog', { name: 'New Location' });
	await expect(dialog).toBeVisible();
	await createLocationThroughWizard(page, dialog, place);
}

export async function addLodging(
	page: Page,
	section: Locator,
	stay: { name: string; price?: string; checkOut?: string }
) {
	await chooseFromAddMenu(section, 'Lodging');
	const dialog = dialogWithHeading(page, 'New Lodging');
	await expect(dialog).toBeVisible();

	// Quick Start: pick a point on the map, then on to the details.
	await pickPointOnMap(page, dialog);
	await dialog.getByRole('button', { name: 'Continue' }).click();

	await dialog.getByRole('textbox', { name: 'Name *' }).fill(stay.name);
	await dialog.getByRole('combobox', { name: 'Type *' }).selectOption({ index: 1 });
	if (stay.price) await dialog.getByRole('spinbutton', { name: 'Price' }).fill(stay.price);
	// Check-in is prefilled from the day; check-out defaults to the next day.
	if (stay.checkOut)
		await typeDate(dialog.getByRole('textbox', { name: 'Check Out' }), stay.checkOut);
	await dialog.getByRole('button', { name: 'Continue' }).click();
	await finishMediaStep(dialog);
	await expect(dialog).toBeHidden();
}

export async function addTransportation(
	page: Page,
	section: Locator,
	leg: { name: string; type: string; from: string; to: string; price?: string }
) {
	await chooseFromAddMenu(section, 'Transportation');
	const dialog = dialogWithHeading(page, 'New Transportation');
	await expect(dialog).toBeVisible();

	// Each end is found by searching for a place and choosing a result.
	for (const [label, query] of [
		['Start Location', leg.from],
		['End Location', leg.to]
	] as const) {
		await dialog.getByRole('textbox', { name: label }).fill(query);
		await dialog
			.getByRole('button', { name: new RegExp(`^${query}`) })
			.first()
			.click();
	}
	await dialog.getByRole('textbox', { name: 'Name *' }).fill(leg.name);
	await dialog.getByRole('combobox', { name: 'Type *' }).selectOption({ label: leg.type });
	if (leg.price) await dialog.getByRole('spinbutton', { name: 'Price' }).fill(leg.price);
	await dialog.getByRole('button', { name: 'Continue' }).click();
	await finishMediaStep(dialog);
	await expect(dialog).toBeHidden();
}

/**
 * The row of a place, note, lodging... inside a section, found by its title: the outermost
 * ancestor of the title that holds exactly one drag grip. A section is never the answer, even
 * when it holds a single row, so the result is always one row's worth of content.
 */
export function planRow(section: Locator, title: string) {
	return section
		.getByText(title, { exact: true })
		.first()
		.locator(
			'xpath=ancestor::*[count(.//*[@aria-label="Drag to reorder"])=1 and not(@data-plan-section)][last()]'
		);
}

/**
 * Tick (or untick) the nth item (from 0) in the checklist editor. Item names are editable
 * fields, not text, so items are found by position: the dialog's checkboxes are the
 * "constrain to collection dates" switch, the "new item" circle, then one per item.
 */
export async function tickChecklistItem(dialog: Locator, index: number, checked = true) {
	await dialog
		.getByRole('checkbox')
		.nth(2 + index)
		.setChecked(checked);
}

/**
 * Drag a row to another place with a real mouse: press the row's grip, move in small steps so
 * the drag library sees a pointer drag, and release over the target. `to` is where to let go.
 */
export async function dragRow(page: Page, row: Locator, to: Locator) {
	const grip = row.getByLabel('Drag to reorder');
	await grip.scrollIntoViewIfNeeded();
	// Measure both ends up front: once a drag starts the library adds a placeholder to the
	// page, which makes a title match more than one element.
	await to.first().scrollIntoViewIfNeeded();
	const target = (await to.first().boundingBox())!;
	const from = (await grip.boundingBox())!;
	const sx = from.x + from.width / 2;
	const sy = from.y + from.height / 2;
	await page.mouse.move(sx, sy);
	await page.mouse.down();
	await page.mouse.move(sx + 6, sy + 6, { steps: 4 });
	await page.mouse.move(target.x + 60, target.y + target.height / 2, { steps: 30 });
	await page.waitForTimeout(300); // let the drop zone settle before releasing
	await page.mouse.up();
}

/** Run an entry from a row's "Item actions" menu. */
export async function itemAction(row: Locator, action: string) {
	await row.getByRole('button', { name: 'Item actions' }).click();
	await row.getByRole('menuitem', { name: action }).click();
}
