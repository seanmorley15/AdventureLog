import { afterEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import LocationCollectionChips from './LocationCollectionChips.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const row = {
	id: 'C1',
	name: 'Lofoten',
	start_date: null,
	end_date: null,
	is_shared: false,
	owner_name: 'me',
	role: 'owner',
	is_linked: true,
	can_link: true,
	can_unlink: true,
	placements: []
};
const sam = { uuid: 's', username: 'sam', first_name: 'Sam', last_name: null, profile_pic: null };

function mockFetch() {
	const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
		const json = (body: unknown) =>
			new Response(JSON.stringify(body), {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			});
		if (String(url).includes('-preview/'))
			return json({
				people_released: [sam],
				includes_you: false,
				visits_deleted: 0,
				others_uploads: 0,
				removed_placements: 1
			});
		if (init?.method === 'DELETE') return json({ linked: false, removed_placements: 1 });
		return json([row]);
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

const realDeletes = (fetchMock: ReturnType<typeof vi.fn>) =>
	fetchMock.mock.calls.filter(
		([u, i]) =>
			!String(u).includes('-preview/') && (i as RequestInit | undefined)?.method === 'DELETE'
	);

afterEach(() => vi.unstubAllGlobals());

describe('LocationCollectionChips remove flow', () => {
	it('asks the server what would happen, then deletes only after confirming', async () => {
		const fetchMock = mockFetch();
		render(LocationCollectionChips, { locationId: 'L1', canManage: true });
		await page.getByRole('button', { name: 'Remove from Lofoten' }).first().click();

		await expect.element(page.getByText(/will get their own copy/)).toBeVisible();
		expect(
			fetchMock.mock.calls.some(
				([u]) => String(u) === '/api/locations/L1/collections/C1/unlink-preview/'
			)
		).toBe(true);
		expect(realDeletes(fetchMock)).toHaveLength(0);

		await page.getByRole('button', { name: 'Remove', exact: true }).click();
		await vi.waitFor(() => expect(realDeletes(fetchMock)).toHaveLength(1));
	});

	it('sends no DELETE when cancelled', async () => {
		const fetchMock = mockFetch();
		render(LocationCollectionChips, { locationId: 'L1', canManage: true });
		await page.getByRole('button', { name: 'Remove from Lofoten' }).first().click();
		await expect.element(page.getByText(/will get their own copy/)).toBeVisible();
		await page.getByRole('button', { name: 'Cancel' }).click();
		expect(realDeletes(fetchMock)).toHaveLength(0);
	});
});
