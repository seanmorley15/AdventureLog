import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import VisitTravelers from './VisitTravelers.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const me = { uuid: 'me', username: 'me', first_name: 'Mia', last_name: 'Lee' };
const sam = { uuid: 'sam', username: 'sam', first_name: null, last_name: null };
const visit = (travelers?: unknown[]) => ({ id: 'v1', travelers }) as never;

describe('VisitTravelers', () => {
	it('hides the leave button when the user is the only traveler', async () => {
		render(VisitTravelers, { visit: visit([me]), currentUserUuid: 'me' });
		await expect.element(page.getByText('Mia Lee').or(page.getByText('You'))).toBeVisible();
		expect(page.getByRole('button').elements()).toHaveLength(0);
	});

	it('shows "I wasn\'t there" when someone else is on the visit too', async () => {
		render(VisitTravelers, { visit: visit([me, sam]), currentUserUuid: 'me' });
		await expect.element(page.getByRole('button', { name: en.visits.i_wasnt_there })).toBeVisible();
	});

	it('shows "I was there too" to a non-traveler', async () => {
		render(VisitTravelers, { visit: visit([sam]), currentUserUuid: 'me' });
		await expect
			.element(page.getByRole('button', { name: en.visits.i_was_there_too }))
			.toBeVisible();
	});

	it('renders nothing without a travelers field', async () => {
		render(VisitTravelers, { visit: visit(undefined), currentUserUuid: 'me' });
		expect(page.getByRole('button').elements()).toHaveLength(0);
	});
});
