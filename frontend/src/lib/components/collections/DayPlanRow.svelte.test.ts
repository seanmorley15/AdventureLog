import { beforeEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import DayPlanRow from './DayPlanRow.svelte';

vi.mock('$app/env/public', () => ({ PUBLIC_CARTO_BASEMAP_API_KEY: '' }));
vi.mock('$app/state', () => ({ page: { data: {} } }));

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const collaborators = [
	{ uuid: 'me', username: 'me', first_name: 'Mia', last_name: 'Lee' },
	{ uuid: 'sam', username: 'sam', first_name: 'Sam', last_name: 'Roe' }
];

function setup(onLogVisit = vi.fn(async () => 'ok' as const)) {
	const row: any = {
		id: 'row1',
		item: { id: 'row1', day_index: 1, span_end_index: 1, logged_visit: null, is_optional: false },
		type: 'location',
		objectId: 'loc1',
		object: { id: 'loc1', name: 'Hut', visits: [] }
	};
	render(DayPlanRow as any, {
		row,
		canModify: true,
		dateFormat: '24h',
		hasProjectedDate: true,
		collection: { id: 'c1', collaborators, itinerary: [row.item], locations: [row.object] },
		currentUserUuid: 'me',
		onLogVisit
	});
	return onLogVisit;
}

describe('DayPlanRow Log visit', () => {
	beforeEach(() => {
		localStorage.clear();
	});

	it('pre-checks the current user and logs exactly the checked people', async () => {
		const onLogVisit = setup();
		await page.getByRole('button', { name: 'Log visit' }).click();
		const [mia, sam] = [page.getByRole('checkbox').first(), page.getByRole('checkbox').nth(1)];
		await expect.element(mia).toBeChecked();
		await mia.click();
		await sam.click();
		await page.getByRole('button', { name: 'Log', exact: true }).click();
		expect(onLogVisit).toHaveBeenCalledWith(expect.anything(), undefined, ['sam']);
	});

	it('disables Log while nobody is checked and never sends an empty list', async () => {
		const onLogVisit = setup();
		await page.getByRole('button', { name: 'Log visit' }).click();
		await page.getByRole('checkbox').first().click();
		await expect.element(page.getByRole('alert')).toHaveTextContent('Pick at least one person');
		const log = page.getByRole('button', { name: 'Log', exact: true });
		await expect.element(log).toBeDisabled();
		expect(onLogVisit).not.toHaveBeenCalled();
	});
});
