import { describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import MoneyInput from './MoneyInput.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

describe('MoneyInput', () => {
	it('shows the amount it was given', async () => {
		render(MoneyInput, {
			label: 'Price',
			value: { amount: 12.5, currency: 'USD' }
		});
		await expect.element(page.getByRole('spinbutton')).toHaveValue(12.5);
	});

	it('shows the placeholder when there is no amount', async () => {
		render(MoneyInput, { label: 'Price', value: { amount: null, currency: 'USD' } });
		await expect.element(page.getByRole('spinbutton')).toHaveValue(null);
		await expect.element(page.getByRole('spinbutton')).toHaveAttribute('placeholder', '0.00');
	});
});
