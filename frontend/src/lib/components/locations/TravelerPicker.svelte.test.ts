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
	it('hides the legend visually but keeps it for screen readers', async () => {
		render(TravelerPicker, { candidates, selected: ['me'], hideLegend: true });
		await expect.element(page.getByText('Who was there')).toHaveClass('sr-only');
	});

	it('shows the legend by default', async () => {
		render(TravelerPicker, { candidates, selected: ['me'] });
		await expect.element(page.getByText('Who was there')).not.toHaveClass('sr-only');
	});

	it('lets anyone be unchecked, including the current user, and shows no warning while someone is', async () => {
		render(TravelerPicker, { candidates, selected: ['me', 'sam'] });
		const [mia, sam] = [page.getByRole('checkbox').first(), page.getByRole('checkbox').nth(1)];
		await mia.click();
		await expect.element(mia).not.toBeChecked();
		await expect.element(sam).toBeChecked();
		await expect.element(sam).not.toHaveAttribute('aria-invalid');
		await expect.element(page.getByRole('alert')).not.toBeInTheDocument();
	});

	it('is invalid when nobody is checked and says so', async () => {
		render(TravelerPicker, { candidates, selected: [] });
		await expect.element(page.getByRole('alert')).toHaveTextContent('Pick at least one person');
		await expect
			.element(page.getByRole('checkbox').first())
			.toHaveAttribute('aria-invalid', 'true');
		await expect.element(page.getByRole('checkbox').nth(1)).toHaveAttribute('aria-invalid', 'true');
	});

	it('allows toggling the last person off and then shows invalid', async () => {
		render(TravelerPicker, { candidates, selected: ['me'] });
		const [mia, sam] = [page.getByRole('checkbox').first(), page.getByRole('checkbox').nth(1)];
		await expect.element(page.getByRole('alert')).not.toBeInTheDocument();
		await mia.click();
		await expect.element(mia).not.toBeChecked();
		await expect.element(page.getByRole('alert')).toBeInTheDocument();
		await expect.element(sam).toHaveAttribute('aria-invalid', 'true');
		await sam.click();
		await expect.element(sam).toBeChecked();
		await expect.element(page.getByRole('alert')).not.toBeInTheDocument();
		await expect.element(sam).not.toHaveAttribute('aria-invalid');
	});

	it('uses the given message id, so controls elsewhere can point at the message', async () => {
		render(TravelerPicker, { candidates, selected: [], messageId: 'outside' });
		await expect.element(page.getByRole('alert')).toHaveAttribute('id', 'outside');
		await expect
			.element(page.getByRole('checkbox').first())
			.toHaveAttribute('aria-describedby', 'outside');
	});
});
