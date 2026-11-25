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
