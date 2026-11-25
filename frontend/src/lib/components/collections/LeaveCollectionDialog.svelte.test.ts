import { afterEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import LeaveCollectionDialog from './LeaveCollectionDialog.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

function mockFetch(preview: { locations: number; others_uploads: number }) {
	const fetchMock = vi.fn(async (_url: string, init?: RequestInit) =>
		_url.includes('dry_run')
			? new Response(JSON.stringify(preview), { status: 200 })
			: new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } })
	);
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe('LeaveCollectionDialog', () => {
	it('offers copies by default, warns about others uploads and sends keep_copies', async () => {
		const fetchMock = mockFetch({ locations: 3, others_uploads: 2 });
		const onleft = vi.fn();
		render(LeaveCollectionDialog, { collectionId: 'c1', onclose: vi.fn(), onleft });

		const keep = page.getByRole('checkbox');
		await expect.element(keep).toBeChecked();
		await expect.element(page.getByText(/Keep your own copies of the 3 locations/)).toBeVisible();
		await expect
			.element(page.getByText(/2 photos, files or activities added by other/))
			.toBeVisible();

		await keep.click();
		await expect.element(page.getByText('These locations will leave your map.')).toBeVisible();
		await page.getByRole('button', { name: 'Leave', exact: true }).click();

		await vi.waitFor(() => expect(onleft).toHaveBeenCalledWith('c1'));
		const post = fetchMock.mock.calls.find(([url]) => !String(url).includes('dry_run'))!;
		expect(JSON.parse(post[1]!.body as string)).toEqual({ keep_copies: false });
	});

	it('hides the checkbox when there are no locations to keep', async () => {
		mockFetch({ locations: 0, others_uploads: 0 });
		render(LeaveCollectionDialog, { collectionId: 'c1', onclose: vi.fn(), onleft: vi.fn() });
		await expect.element(page.getByRole('button', { name: 'Leave', exact: true })).toBeVisible();
		await expect.element(page.getByRole('checkbox')).not.toBeInTheDocument();
	});
});
