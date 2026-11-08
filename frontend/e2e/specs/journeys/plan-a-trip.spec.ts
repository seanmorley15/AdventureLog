import { test, expect } from '../../fixtures';
import { newCredentials, signUp } from '../../support/accounts';
import {
	createLocationThroughWizard,
	openNewLocation,
	SAMPLE_IMAGE
} from '../../support/locations';
import {
	addChecklist,
	addExisting,
	addLodging,
	addNewLocation,
	addNote,
	addTransportation,
	createTrip,
	dragRow,
	itemAction,
	planRow,
	planSection,
	tickChecklistItem
} from '../../support/trip';

// A brand-new user plans a four-day trip from scratch, entirely through the UI.
// Every step is a test.step so the report reads like the story of the session.
test.use({ storageState: { cookies: [], origins: [] } });
test.describe.configure({ mode: 'serial', timeout: 300_000 });

test('plan a trip to Paris', async ({ page }) => {
	await test.step('sign up and land on an empty dashboard', async () => {
		await signUp(page, newCredentials('traveller'));
		await expect(page).toHaveURL(/\/dashboard/);
		await expect(page.getByText('Your travel journal is empty')).toBeVisible();
	});

	await test.step('add three places to my locations', async () => {
		const places = [
			{
				name: 'Eiffel Tower',
				tags: ['iconic'],
				description: 'The **wrought-iron** tower.',
				image: SAMPLE_IMAGE
			},
			{ name: 'Louvre', tags: ['art'], description: "The world's largest art museum." },
			{ name: 'Mont Saint-Michel', tags: ['day trip'], description: 'A tidal island abbey.' }
		];
		for (const place of places) {
			const dialog = await openNewLocation(page);
			await createLocationThroughWizard(page, dialog, {
				...place,
				category: 'Landmark',
				visit: { start: '06/11/2027' }
			});
		}
		await page.reload();
		for (const place of places) {
			await expect(page.locator('.card', { hasText: place.name }).first()).toBeVisible();
		}
	});

	await test.step('create a four-day trip', async () => {
		await createTrip(page, {
			name: 'Paris 2027',
			description: 'Four days of **art** and food.',
			start: '06/10/2027',
			end: '06/13/2027'
		});
		for (const day of [1, 2, 3, 4]) {
			await expect(planSection(page, day)).toBeVisible();
		}
	});

	await test.step('put existing places on days', async () => {
		await addExisting(page, planSection(page, 1), ['Eiffel Tower']);
		await addExisting(page, planSection(page, 1), ['Louvre']);
		await expect(planSection(page, 1)).toContainText('Eiffel Tower');
		await expect(planSection(page, 1)).toContainText('Louvre');
	});

	await test.step('add a note and a checklist', async () => {
		await addNote(page, planSection(page, 2), {
			name: 'Book the Seine cruise',
			body: 'Ask about the **sunset** sailing.',
			link: 'https://example.com/cruise'
		});
		await expect(planSection(page, 2)).toContainText('Book the Seine cruise');

		await addChecklist(page, planSection(page, 'global'), {
			name: 'Packing',
			items: ['Passport', 'Charger', 'Umbrella', 'Walking shoes']
		});
		await expect(planSection(page, 'global')).toContainText('Packing');
	});

	await test.step('create a new place, a hotel and a train from inside the trip', async () => {
		await addNewLocation(page, planSection(page, 2), {
			name: 'Café de Flore',
			category: 'Landmark',
			tags: ['coffee'],
			visit: { start: '06/11/2027' }
		});
		await expect(planSection(page, 2)).toContainText('Café de Flore');

		await addLodging(page, planSection(page, 1), {
			name: 'Hôtel Lutetia',
			price: '240',
			checkOut: '06/13/2027'
		});
		await expect(planSection(page, 1)).toContainText('Hôtel Lutetia');

		await addTransportation(page, planSection(page, 3), {
			name: 'Train to Mont Saint-Michel',
			type: '🚆 Train',
			from: 'Paris Montparnasse',
			to: 'Pontorson',
			price: '85'
		});
		await expect(planSection(page, 3)).toContainText('Train to Mont Saint-Michel');
	});

	await test.step('move things around the plan', async () => {
		// Drag the Louvre from day 1 onto day 2 with the mouse.
		await dragRow(
			page,
			planRow(planSection(page, 1), 'Louvre'),
			planRow(planSection(page, 2), 'Book the Seine cruise')
		);
		await expect(planSection(page, 2)).toContainText('Louvre');
		await expect(planSection(page, 1)).not.toContainText('Louvre');

		// Reorder inside day 2: put the note above the Louvre.
		const order = async () => {
			const text = await planSection(page, 2).innerText();
			return ['Louvre', 'Book the Seine cruise'].sort((a, b) => text.indexOf(a) - text.indexOf(b));
		};
		const before = await order();
		await dragRow(
			page,
			planRow(planSection(page, 2), before[1]),
			planRow(planSection(page, 2), before[0])
		);
		await expect.poll(order).toEqual([before[1], before[0]]);

		// Move the Eiffel Tower to day 3 through its "Edit placement" dialog.
		await itemAction(planRow(planSection(page, 1), 'Eiffel Tower'), 'Edit placement');
		const dialog = page
			.getByRole('dialog')
			.filter({ has: page.getByRole('heading', { name: 'Edit placement' }) })
			.last();
		await dialog
			.getByRole('combobox', { name: 'Where' })
			.selectOption({ label: 'Day 3 · Jun 12, 2027' });
		await dialog.getByRole('button', { name: 'Save' }).click();
		await expect(dialog).toBeHidden();
		await expect(planSection(page, 3)).toContainText('Eiffel Tower');
		await expect(planSection(page, 1)).not.toContainText('Eiffel Tower');
	});

	await test.step('edit the checklist and the note', async () => {
		// Tick two packing items.
		await itemAction(planRow(planSection(page, 'global'), 'Packing'), 'Edit details');
		const checklist = page.getByRole('dialog').last();
		await tickChecklistItem(checklist, 0);
		await tickChecklistItem(checklist, 1);
		await checklist.getByRole('button', { name: 'Save' }).click();
		await expect(checklist).toBeHidden();
		await expect(planRow(planSection(page, 'global'), 'Packing')).toContainText('2/4');

		// Rename the note.
		await itemAction(planRow(planSection(page, 2), 'Book the Seine cruise'), 'Edit details');
		const note = page.getByRole('dialog').last();
		await note.getByRole('textbox', { name: 'Name*' }).fill('Book the sunset cruise');
		await note.getByRole('button', { name: 'Save' }).click();
		await expect(note).toBeHidden();
		await expect(planSection(page, 2)).toContainText('Book the sunset cruise');
		await expect(planSection(page, 2)).not.toContainText('Book the Seine cruise');
	});

	await test.step('take a place out of the trip without losing it', async () => {
		await itemAction(planRow(planSection(page, 2), 'Café de Flore'), 'Remove from Collection');
		await expect(planSection(page, 2)).not.toContainText('Café de Flore');

		await page.goto('/locations');
		await expect(page.locator('.card', { hasText: 'Café de Flore' }).first()).toBeVisible();
		await page.goBack();
		await expect(page.getByRole('heading', { name: 'Paris 2027', level: 1 })).toBeVisible();
	});

	await test.step('the other tabs agree with the plan', async () => {
		const tab = (name: string) => page.getByRole('tab', { name });
		// Switching tabs navigates, so wait for the new tab to be the selected one.
		const openTab = async (name: string) => {
			await tab(name).click();
			await expect(tab(name)).toHaveAttribute('aria-selected', 'true');
		};

		await openTab('Trip Costs');
		// The hotel ($240) and the train ($85) add up.
		await expect(page.getByText('$325.00').first()).toBeVisible();

		await openTab('Calendar');
		await expect(page.getByText('Hôtel Lutetia').first()).toBeVisible();

		await openTab('All Items');
		for (const name of ['Eiffel Tower', 'Louvre', 'Hôtel Lutetia']) {
			await expect(page.getByText(name).first()).toBeVisible();
		}

		await openTab('Plan');
		await expect(planSection(page, 1)).toBeVisible();
		// The map is drawn (its tiles are stubbed, so it is an empty canvas).
		await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible();
	});

	await test.step('everything is still there after a reload', async () => {
		await page.reload();
		await expect(page.getByRole('heading', { name: 'Paris 2027', level: 1 })).toBeVisible();
		await expect(planSection(page, 1)).toContainText('Hôtel Lutetia');
		await expect(planSection(page, 1)).not.toContainText('Eiffel Tower');
		await expect(planSection(page, 1)).not.toContainText('Louvre');
		await expect(planSection(page, 2)).toContainText('Louvre');
		await expect(planSection(page, 2)).toContainText('Book the sunset cruise');
		// Café de Flore was taken out of the trip; it must stay out.
		await expect(planSection(page, 2)).not.toContainText('Café de Flore');
		await expect(planSection(page, 3)).toContainText('Eiffel Tower');
		await expect(planSection(page, 3)).toContainText('Train to Mont Saint-Michel');
		await expect(planRow(planSection(page, 'global'), 'Packing')).toContainText('2/4');
	});

	await test.step('find a place with the search palette', async () => {
		await page.keyboard.press('Control+k');
		const palette = page.locator('dialog.modal-open');
		await expect(palette).toBeVisible();
		await palette.getByPlaceholder('Search').fill('Louvre');
		// Choosing the result opens the place (as a drawer over the current page).
		await palette
			.getByRole('button', { name: /Louvre/ })
			.first()
			.click();
		await expect(palette).toBeHidden();
		const drawer = page.getByRole('dialog').filter({ hasText: 'Louvre' });
		await expect(drawer.first()).toBeVisible();
		await page.keyboard.press('Escape');
	});

	await test.step('open and close the About dialog from the navbar menu', async () => {
		await page
			.locator('div.dropdown', { has: page.locator('button', { hasText: 'About AdventureLog' }) })
			.locator('> button[aria-haspopup="menu"]')
			.click();
		await page.getByRole('button', { name: 'About AdventureLog' }).click();
		const about = page.getByRole('dialog').filter({ hasText: 'AdventureLog' }).last();
		await expect(about).toBeVisible();
		await about.getByRole('button', { name: 'Close' }).first().click();
		await expect(about).toBeHidden();
	});
});
