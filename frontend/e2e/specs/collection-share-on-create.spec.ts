import { test, expect } from '../fixtures';
import { openNewCollection } from '../support/trip';

// #967: share a collection straight from the form that creates it.
test.describe('share while creating a collection', () => {
	test('"Save & share" creates the collection and opens its share sheet', async ({ page }) => {
		const name = `Shared Trip ${Date.now().toString(36)}`;
		const form = await openNewCollection(page);
		await form.getByRole('textbox', { name: 'Name*' }).fill(name);
		await form.getByRole('button', { name: 'Save & share' }).click();

		// The form gives way to the share sheet, open on People with the invite controls.
		await expect(form).toBeHidden();
		const sheet = page.getByRole('dialog', { name: 'Share' });
		await expect(sheet).toBeVisible();
		await expect(sheet.getByRole('combobox', { name: 'Role' })).toBeVisible();

		// Closing it leaves the new collection in the list.
		await sheet.getByRole('button', { name: 'Close' }).first().click();
		await expect(sheet).toBeHidden();
		await expect(page.getByRole('link', { name }).first()).toBeVisible();
	});

	test('"Save" alone creates the collection without opening the share sheet', async ({ page }) => {
		const name = `Private Trip ${Date.now().toString(36)}`;
		const form = await openNewCollection(page);
		await form.getByRole('textbox', { name: 'Name*' }).fill(name);
		await form.getByRole('button', { name: 'Save', exact: true }).click();

		await expect(form).toBeHidden();
		await expect(page.getByRole('dialog', { name: 'Share' })).toHaveCount(0);
		await expect(page.getByRole('link', { name }).first()).toBeVisible();
	});
});
