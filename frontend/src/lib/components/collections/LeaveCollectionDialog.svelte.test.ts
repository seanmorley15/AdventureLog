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
		_url.includes('-preview/')
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
		await expect
			.element(
				page.getByText(
					/These locations will leave your map, along with the photos, files and activities you added to them/
				)
			)
			.toBeVisible();
		await page.getByRole('button', { name: 'Leave', exact: true }).click();

		await vi.waitFor(() => expect(onleft).toHaveBeenCalledWith('c1'));
		expect(String(fetchMock.mock.calls[0][0])).toBe('/api/collections/c1/leave-preview/');
		expect(fetchMock.mock.calls[0][1]?.method ?? 'GET').toBe('GET');
		const post = fetchMock.mock.calls.find(([url]) => !String(url).includes('-preview/'))!;
		expect(JSON.parse(post[1]!.body as string)).toEqual({ keep_copies: false });
	});

	it('hides the checkbox when there are no locations to keep', async () => {
		mockFetch({ locations: 0, others_uploads: 0 });
		render(LeaveCollectionDialog, { collectionId: 'c1', onclose: vi.fn(), onleft: vi.fn() });
		await expect.element(page.getByRole('button', { name: 'Leave', exact: true })).toBeVisible();
		await expect.element(page.getByRole('checkbox')).not.toBeInTheDocument();
	});

	it('keeps Leave disabled until the preview loads', async () => {
		let release: (r: Response) => void = () => {};
		vi.stubGlobal(
			'fetch',
			vi.fn(() => new Promise<Response>((resolve) => (release = resolve)))
		);
		render(LeaveCollectionDialog, { collectionId: 'c1', onclose: vi.fn(), onleft: vi.fn() });
		await expect.element(page.getByRole('button', { name: 'Leave', exact: true })).toBeDisabled();
		release(new Response(JSON.stringify({ locations: 1, others_uploads: 0 }), { status: 200 }));
		await expect.element(page.getByRole('button', { name: 'Leave', exact: true })).toBeEnabled();
	});

	it('shows an error when the preview fails and retry reloads it', async () => {
		let calls = 0;
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => {
				calls += 1;
				return calls === 1
					? new Response(JSON.stringify({ detail: 'Nope' }), { status: 500 })
					: new Response(JSON.stringify({ locations: 2, others_uploads: 0 }), { status: 200 });
			})
		);
		render(LeaveCollectionDialog, { collectionId: 'c1', onclose: vi.fn(), onleft: vi.fn() });
		await expect.element(page.getByRole('alert')).toBeVisible();
		await expect.element(page.getByRole('button', { name: 'Leave', exact: true })).toBeDisabled();
		await page.getByRole('button', { name: 'Try again' }).click();
		await expect.element(page.getByRole('checkbox')).toBeVisible();
		await expect.element(page.getByRole('button', { name: 'Leave', exact: true })).toBeEnabled();
	});

	it('sends only one POST on a double click', async () => {
		const fetchMock = mockFetch({ locations: 1, others_uploads: 0 });
		render(LeaveCollectionDialog, { collectionId: 'c1', onclose: vi.fn(), onleft: vi.fn() });
		const leave = page.getByRole('button', { name: 'Leave', exact: true });
		await expect.element(leave).toBeEnabled();
		const el = (await leave.element()) as HTMLButtonElement;
		el.click();
		el.click();
		await vi.waitFor(() =>
			expect(fetchMock.mock.calls.filter(([u]) => !String(u).includes('-preview/'))).toHaveLength(1)
		);
	});
});
