import { afterEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import CollectionShareSheet from './CollectionShareSheet.svelte';

// The app barrel pulls in SvelteKit env modules that do not exist under the test runner.
vi.mock('#lib/index.js', () => ({ copyToClipboard: vi.fn() }));

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const sharing = {
	owner: { uuid: 'o', username: 'owner', first_name: 'Olive', last_name: null, is_owner: true },
	members: [{ uuid: 'm1', username: 'sam', first_name: 'Sam', last_name: null, role: 'editor' }],
	invites: [],
	guest_links: [],
	visibility: 'private',
	story_groups: {},
	comment_access: 'none',
	share_secret: 's',
	allow_public_links: false
};

function mockFetch() {
	const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
		const method = init?.method ?? 'GET';
		const json = (body: unknown, status = 200) =>
			new Response(JSON.stringify(body), {
				status,
				headers: { 'Content-Type': 'application/json' }
			});
		if (url.endsWith('/sharing/')) return json(sharing);
		if (url.includes('add-travelers') && url.includes('-preview/'))
			return json({ visits: 2, locations: 1 });
		if (url.includes('add-travelers')) return json({ visits: 2, locations: 1 });
		if (url.includes('/removal-preview/')) return json({ locations: 1, others_uploads: 0 });
		if (method === 'DELETE') return new Response(null, { status: 204 });
		return json({});
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

const real = (calls: unknown[][], method: string, part: string) =>
	calls.filter(
		([u, i]) =>
			String(u).includes(part) &&
			!String(u).includes('-preview/') &&
			(i as RequestInit | undefined)?.method === method
	);

afterEach(() => vi.unstubAllGlobals());

describe('CollectionShareSheet confirms', () => {
	// DeleteWarning dispatches close and then confirm after a 150ms delay; the real
	// request must still go out once.
	it('adds the person to the visits after the confirm', async () => {
		const fetchMock = mockFetch();
		render(CollectionShareSheet, {
			collection: {
				id: 'c1',
				name: 'Trip',
				shared_with: ['m1'],
				collaborators: [],
				is_public: false
			},
			onClose: vi.fn()
		});
		await page.getByRole('button', { name: "Add to this trip's visits" }).click();
		await page.getByRole('button', { name: 'Add to visits', exact: true }).click();
		await vi.waitFor(() =>
			expect(real(fetchMock.mock.calls, 'POST', '/add-travelers/')).toHaveLength(1)
		);
		const preview = fetchMock.mock.calls.find(([u]) =>
			String(u).includes('add-travelers-preview')
		)!;
		expect(preview[0]).toBe('/api/collections/c1/add-travelers-preview/?user_uuids=m1');
		expect(preview[1]?.method).toBe('GET');
	});

	it('removes the member after the confirm', async () => {
		const fetchMock = mockFetch();
		render(CollectionShareSheet, {
			collection: {
				id: 'c1',
				name: 'Trip',
				shared_with: ['m1'],
				collaborators: [],
				is_public: false
			},
			onClose: vi.fn()
		});
		await page.getByRole('button', { name: 'Remove Sam' }).click();
		await page.getByRole('button', { name: 'Remove', exact: true }).click();
		await vi.waitFor(() =>
			expect(real(fetchMock.mock.calls, 'DELETE', '/members/m1/')).toHaveLength(1)
		);
		const preview = fetchMock.mock.calls.find(([u]) => String(u).includes('removal-preview'))!;
		expect(preview[0]).toBe('/api/collections/c1/members/m1/removal-preview/');
		expect(preview[1]?.method).toBe('GET');
	});
});
