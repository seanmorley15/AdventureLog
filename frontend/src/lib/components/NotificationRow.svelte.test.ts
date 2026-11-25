import { afterEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../locales/en.json';
import NotificationRow from './NotificationRow.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const single = {
	id: 'n1',
	kind: 'visit_traveler_added',
	actor: { name: 'Mia Lee', username: null, profile_pic: null, can_view_profile: false },
	visit_id: 'v1',
	location_id: 'l1',
	location_name: 'Hut',
	collection_id: 'c1',
	collection_name: 'Lofoten',
	count: 1,
	locations: 1,
	start_date: '2026-06-02',
	end_date: '2026-06-02',
	created_at: new Date().toISOString(),
	read: false
} as never;

afterEach(() => vi.unstubAllGlobals());

describe('NotificationRow', () => {
	it('says who added you, where, and links to the place', async () => {
		render(NotificationRow, { item: single });
		await expect.element(page.getByText('Mia Lee added you to a visit at Hut')).toBeVisible();
		await expect.element(page.getByRole('link')).toHaveAttribute('href', '/locations/l1');
		await expect
			.element(page.getByRole('img', { name: en.notifications.unread }))
			.toBeInTheDocument();
	});

	it('is the summary form for several visits, linking to the trip, with no remove button', async () => {
		render(NotificationRow, { item: { ...(single as object), count: 5, visit_id: null } as never });
		await expect.element(page.getByText('Mia Lee added you to 5 visits on Lofoten')).toBeVisible();
		await expect.element(page.getByRole('link')).toHaveAttribute('href', '/collections/c1');
		expect(page.getByRole('button').elements()).toHaveLength(0);
	});

	it('leaves the visit and hides the button afterwards', async () => {
		const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
		vi.stubGlobal('fetch', fetchSpy);
		const onremoved = vi.fn();
		render(NotificationRow, { item: single, onremoved });
		await page.getByRole('button', { name: en.notifications.remove_me }).click();
		expect(onremoved).toHaveBeenCalledWith(single);
		expect(fetchSpy).toHaveBeenCalledWith('/api/visits/v1/leave/', { method: 'POST' });
		await vi.waitFor(() => expect(page.getByRole('button').elements()).toHaveLength(0));
	});

	it('keeps the button when leaving fails', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 500 })));
		const onremoved = vi.fn();
		render(NotificationRow, { item: single, onremoved });
		await page.getByRole('button', { name: en.notifications.remove_me }).click();
		expect(onremoved).not.toHaveBeenCalled();
		await expect
			.element(page.getByRole('button', { name: en.notifications.remove_me }))
			.toBeVisible();
	});

	it('does not name a place the person can no longer read', async () => {
		render(NotificationRow, {
			item: { ...(single as object), location_id: null, location_name: '' } as never
		});
		await expect
			.element(page.getByText('Mia Lee added you to a visit', { exact: true }))
			.toBeVisible();
	});
});
