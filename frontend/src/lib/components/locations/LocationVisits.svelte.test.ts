import { afterEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import LocationVisits from './LocationVisits.svelte';

vi.mock('$app/env/public', () => ({ PUBLIC_CARTO_BASEMAP_API_KEY: '' }));
vi.mock('$app/state', () => ({ page: { data: { user: { uuid: 'me', username: 'me' } } } }));

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

afterEach(() => vi.unstubAllGlobals());

const me = { uuid: 'me', username: 'me', first_name: 'Mia', last_name: '', profile_pic: null };
const sam = { uuid: 'sam', username: 'sam', first_name: 'Sam', last_name: '', profile_pic: null };

function stubFetch(candidates: unknown[]) {
	const spy = vi.fn(async (url: string, init?: RequestInit) => {
		if (url.includes('/traveler-candidates/')) return Response.json(candidates);
		if (url === '/api/visits/' && init?.method === 'POST') {
			const body = JSON.parse(init.body as string);
			return Response.json(
				{ id: 'v1', activities: [], travelers: [me], ...body, location: 'L1' },
				{ status: 201 }
			);
		}
		return Response.json({});
	});
	vi.stubGlobal('fetch', spy);
	return spy;
}

async function addTodaysVisit(spy: ReturnType<typeof stubFetch>) {
	await vi.waitFor(() =>
		expect(spy.mock.calls.some(([u]) => String(u).includes('traveler-candidates'))).toBe(true)
	);
	await page.getByRole('button', { name: en.adventures.add_today_visit }).first().click();
	await vi.waitFor(() =>
		expect(spy.mock.calls.some(([u, i]) => u === '/api/visits/' && i?.method === 'POST')).toBe(true)
	);
	const [, init] = spy.mock.calls.find(([u, i]) => u === '/api/visits/' && i?.method === 'POST')!;
	return JSON.parse(init!.body as string);
}

describe('LocationVisits creating a visit', () => {
	it('names you when there is no one else to pick', async () => {
		const spy = stubFetch([me]);
		render(LocationVisits, { objectId: 'L1', visits: [] });
		expect((await addTodaysVisit(spy)).traveler_uuids).toEqual(['me']);
	});

	it('sends the picked list when the picker is shown', async () => {
		const spy = stubFetch([me, sam]);
		render(LocationVisits, { objectId: 'L1', visits: [] });
		await expect.element(page.getByText('Sam')).toBeVisible();
		expect((await addTodaysVisit(spy)).traveler_uuids).toEqual(['me']);
	});
});
