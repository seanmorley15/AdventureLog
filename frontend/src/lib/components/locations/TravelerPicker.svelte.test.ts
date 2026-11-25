import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import TravelerPicker from './TravelerPicker.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const candidates = [
	{ uuid: 'me', username: 'me', first_name: 'Mia', last_name: 'Lee' },
	{ uuid: 'sam', username: 'sam', first_name: null, last_name: null }
];

describe('TravelerPicker', () => {
	it('keeps the locked person checked', async () => {
		render(TravelerPicker, { candidates, selected: ['me'], lockedUuid: 'me' });
		const mia = page.getByRole('checkbox').first();
		await expect.element(mia).toBeChecked();
		await expect.element(mia).toBeDisabled();
	});

	it('checks and unchecks the others, but never the last person', async () => {
		render(TravelerPicker, { candidates, selected: ['me'] });
		const [mia, sam] = [page.getByRole('checkbox').first(), page.getByRole('checkbox').nth(1)];
		await expect.element(mia).toBeDisabled(); // the only one on the visit
		await sam.click();
		await expect.element(sam).toBeChecked();
		await expect.element(mia).toBeEnabled();
		await mia.click();
		await expect.element(mia).not.toBeChecked();
		await expect.element(sam).toBeDisabled(); // now the last one
	});

	it('keeps the locked person checked while others are toggled', async () => {
		render(TravelerPicker, { candidates, selected: ['me', 'sam'], lockedUuid: 'me' });
		const [mia, sam] = [page.getByRole('checkbox').first(), page.getByRole('checkbox').nth(1)];
		await expect.element(mia).toBeChecked();
		await expect.element(mia).toBeDisabled();
		await expect.element(sam).toBeEnabled();
		await sam.click();
		await expect.element(sam).not.toBeChecked();
		await expect.element(mia).toBeChecked();
		await sam.click();
		await expect.element(sam).toBeChecked();
	});
});
