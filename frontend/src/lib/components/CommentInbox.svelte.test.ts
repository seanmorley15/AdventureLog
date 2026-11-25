import { afterEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../locales/en.json';
import CommentInbox from './CommentInbox.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

afterEach(() => vi.unstubAllGlobals());

describe('CommentInbox', () => {
	it('keeps the known notification count when only the notifications request fails', async () => {
		let notificationCalls = 0;
		vi.stubGlobal(
			'fetch',
			vi.fn(async (url: string) => {
				const json = (body: unknown, status = 200) =>
					new Response(JSON.stringify(body), { status });
				if (String(url).includes('/api/comments/inbox/?'))
					return json({ unread_count: 1, comments: [] });
				if (String(url).includes('/api/notifications/mark-read/')) return json({}, 500);
				notificationCalls += 1;
				return notificationCalls === 1
					? json({ unread_count: 2, results: [] })
					: json({ detail: 'down' }, 500);
			})
		);
		render(CommentInbox, { initialUnread: 0 });
		const bell = page.getByRole('button', { name: 'Inbox' });
		await bell.click();
		await expect.element(page.getByText('3', { exact: true })).toBeVisible();
		await bell.click();
		await bell.click();
		await vi.waitFor(() => expect(notificationCalls).toBe(2));
		await expect.element(page.getByText('3', { exact: true })).toBeVisible();
	});
});

const note = {
	id: 'n1',
	kind: 'visit_traveler_added',
	actor: { name: 'Mia Lee', username: null, profile_pic: null, can_view_profile: false },
	visit_id: 'v1',
	location_id: 'l1',
	location_name: 'Hut',
	collection_id: null,
	collection_name: '',
	count: 1,
	locations: 1,
	start_date: '2026-06-02',
	end_date: '2026-06-02',
	created_at: new Date().toISOString(),
	read: false
};

function stubFetch(leaveStatus: number) {
	const spy = vi.fn(async (url: string) => {
		if (url.startsWith('/api/notifications/?')) {
			return Response.json({ results: [note], unread_count: 1 });
		}
		if (url.startsWith('/api/comments/inbox/?')) {
			return Response.json({ unread_count: 0, comments: [] });
		}
		if (url === '/api/notifications/mark-read/') return Response.json({ unread_count: 0 });
		return new Response(null, { status: leaveStatus });
	});
	vi.stubGlobal('fetch', spy);
	return spy;
}

describe('CommentInbox notifications', () => {
	it('drops the row after Remove me succeeds', async () => {
		stubFetch(204);
		render(CommentInbox, { initialUnread: 1 });
		await page.getByRole('button', { name: en.comments.inbox_title }).click();
		await expect.element(page.getByText('Mia Lee added you to a visit at Hut')).toBeVisible();
		await page.getByRole('button', { name: en.notifications.remove_me }).click();
		await vi.waitFor(() =>
			expect(page.getByText('Mia Lee added you to a visit at Hut').elements()).toHaveLength(0)
		);
	});

	it('keeps the row when Remove me fails', async () => {
		stubFetch(500);
		render(CommentInbox, { initialUnread: 1 });
		await page.getByRole('button', { name: en.comments.inbox_title }).click();
		await page.getByRole('button', { name: en.notifications.remove_me }).click();
		await expect.element(page.getByText('Mia Lee added you to a visit at Hut')).toBeVisible();
	});
});
