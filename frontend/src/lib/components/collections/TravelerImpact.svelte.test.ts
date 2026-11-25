import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import TravelerImpact from './TravelerImpact.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const sam = { uuid: 's', username: 'sam', first_name: 'Sam', last_name: 'Lee', profile_pic: null };
const kim = { uuid: 'k', username: 'kim', first_name: '', last_name: '', profile_pic: null };
const me = { uuid: 'me', username: 'me', first_name: 'Me', last_name: '', profile_pic: null };

describe('TravelerImpact', () => {
	it('says who gets a copy, what others keep and what is deleted', async () => {
		render(TravelerImpact, { people: [sam, kim], visitsDeleted: 2, othersUploads: 3 });
		await expect
			.element(
				page.getByText('2 people who traveled there will get their own copy, with their visits.')
			)
			.toBeVisible();
		await expect.element(page.getByText('Sam Lee')).toBeVisible();
		await expect.element(page.getByText('kim', { exact: true })).toBeVisible();
		await expect
			.element(page.getByText(/2 visits that only the people getting a copy were on/))
			.toBeVisible();
		await expect
			.element(page.getByText(/3 photos, files or activities that other people added/))
			.toBeVisible();
		await expect.element(page.getByText('Everyone else keeps the place as it is.')).toBeVisible();
	});

	it('names you as "you" and leaves you out of the list', async () => {
		render(TravelerImpact, { people: [me, sam], includesYou: true, meUuid: 'me' });
		await expect
			.element(page.getByText('You will get your own copy of it, with your visits.'))
			.toBeVisible();
		await expect
			.element(
				page.getByText('1 person who traveled there will get their own copy, with their visits.')
			)
			.toBeVisible();
		await expect.element(page.getByText('Sam Lee')).toBeVisible();
		await expect.element(page.getByText('Me', { exact: true })).not.toBeInTheDocument();
	});

	it('shows only your own line when nobody else is affected', async () => {
		render(TravelerImpact, { people: [me], includesYou: true, meUuid: 'me' });
		await expect.element(page.getByText(/You will get your own copy/)).toBeVisible();
		await expect.element(page.getByText(/who traveled there/)).not.toBeInTheDocument();
	});

	it('renders nothing when nobody is affected', async () => {
		render(TravelerImpact, { people: [], visitsDeleted: 0, othersUploads: 0 });
		await expect.element(page.getByTestId('traveler-impact')).not.toBeInTheDocument();
	});

	it('drops the "others keep it" line when the place itself goes', async () => {
		render(TravelerImpact, { people: [sam], places: 4, othersKeep: false });
		await expect.element(page.getByText('They get a copy of 4 places.')).toBeVisible();
		await expect.element(page.getByText(/Everyone else keeps/)).not.toBeInTheDocument();
	});
});
