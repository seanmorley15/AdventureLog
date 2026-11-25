import { afterEach, describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import UnlinkPlaceDialog from './UnlinkPlaceDialog.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const sam = { uuid: 's', username: 'sam', first_name: 'Sam', last_name: null, profile_pic: null };
const quietPreview = {
	people_released: [],
	includes_you: false,
	visits_deleted: 0,
	others_uploads: 0,
	removed_placements: 0
};

function mockFetch(preview: object = quietPreview) {
	const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
		if (String(url).includes('dry_run'))
			return new Response(JSON.stringify(preview), { status: 200 });
		return new Response(JSON.stringify({ linked: false, removed_placements: 2 }), {
			status: 200,
			headers: { 'Content-Type': 'application/json' }
		});
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

const real = (fetchMock: ReturnType<typeof vi.fn>) =>
	fetchMock.mock.calls.filter(
		([u, i]) =>
			!String(u).includes('dry_run') && (i as RequestInit | undefined)?.method === 'DELETE'
	);

const props = () => ({
	locationId: 'L1',
	collectionId: 'C1',
	collectionName: 'Lofoten',
	onunlinked: vi.fn(),
	onclose: vi.fn()
});

afterEach(() => vi.unstubAllGlobals());

describe('UnlinkPlaceDialog', () => {
	it('fetches the dry run first and sends the real DELETE only after Remove', async () => {
		const fetchMock = mockFetch({
			...quietPreview,
			people_released: [sam],
			visits_deleted: 1,
			others_uploads: 2,
			removed_placements: 2
		});
		const p = props();
		render(UnlinkPlaceDialog, p);

		await expect
			.element(
				page.getByText('1 person who traveled there will get their own copy, with their visits.')
			)
			.toBeVisible();
		await expect.element(page.getByText('Sam')).toBeVisible();
		await expect
			.element(page.getByText('It also leaves 2 stops on the plan of Lofoten.'))
			.toBeVisible();
		expect(String(fetchMock.mock.calls[0][0])).toBe('/api/locations/L1/collections/C1/?dry_run=1');
		expect(real(fetchMock)).toHaveLength(0);

		await page.getByRole('button', { name: 'Remove', exact: true }).click();
		await vi.waitFor(() => expect(p.onunlinked).toHaveBeenCalledWith(2));
		expect(real(fetchMock)).toHaveLength(1);
		expect(String(real(fetchMock)[0][0])).toBe('/api/locations/L1/collections/C1/');
	});

	it('sends nothing when cancelled', async () => {
		const fetchMock = mockFetch({ ...quietPreview, people_released: [sam] });
		const p = props();
		render(UnlinkPlaceDialog, p);
		await expect.element(page.getByText(/will get their own copy/)).toBeVisible();
		await page.getByRole('button', { name: 'Cancel' }).click();
		await vi.waitFor(() => expect(p.onclose).toHaveBeenCalled());
		expect(real(fetchMock)).toHaveLength(0);
		expect(p.onunlinked).not.toHaveBeenCalled();
	});

	it('sends one DELETE on a double click', async () => {
		const fetchMock = mockFetch({ ...quietPreview, people_released: [sam] });
		render(UnlinkPlaceDialog, props());
		const remove = page.getByRole('button', { name: 'Remove', exact: true });
		await expect.element(remove).toBeEnabled();
		const el = (await remove.element()) as HTMLButtonElement;
		el.click();
		el.click();
		await vi.waitFor(() => expect(real(fetchMock)).toHaveLength(1));
	});

	it('blocks Remove when the preview fails, and retry loads it', async () => {
		let calls = 0;
		const fetchMock = vi.fn(async (url: string) => {
			if (!String(url).includes('dry_run')) return new Response('{}', { status: 200 });
			calls += 1;
			return calls === 1
				? new Response('{}', { status: 500 })
				: new Response(JSON.stringify({ ...quietPreview, people_released: [sam] }), {
						status: 200
					});
		});
		vi.stubGlobal('fetch', fetchMock);
		render(UnlinkPlaceDialog, props());
		await expect.element(page.getByRole('alert')).toBeVisible();
		await expect.element(page.getByRole('button', { name: 'Remove', exact: true })).toBeDisabled();
		await page.getByRole('button', { name: 'Try again' }).click();
		await expect.element(page.getByText(/will get their own copy/)).toBeVisible();
		await expect.element(page.getByRole('button', { name: 'Remove', exact: true })).toBeEnabled();
		expect(real(fetchMock)).toHaveLength(0);
	});

	it('removes without a dialog when nobody is affected and the plan is light', async () => {
		const fetchMock = mockFetch();
		const p = props();
		render(UnlinkPlaceDialog, p);
		await vi.waitFor(() => expect(p.onunlinked).toHaveBeenCalled());
		expect(real(fetchMock)).toHaveLength(1);
		expect(p.onclose).toHaveBeenCalled();
	});

	it('still asks when only the plan is affected beyond the quiet limit', async () => {
		mockFetch({ ...quietPreview, removed_placements: 3 });
		const p = { ...props(), quietPlacements: 1 };
		render(UnlinkPlaceDialog, p);
		await expect
			.element(page.getByText('It also leaves 3 stops on the plan of Lofoten.'))
			.toBeVisible();
		expect(p.onunlinked).not.toHaveBeenCalled();
	});

	it('stays open with the button usable again when the real DELETE fails', async () => {
		const fetchMock = vi.fn(async (url: string) =>
			String(url).includes('dry_run')
				? new Response(JSON.stringify({ ...quietPreview, people_released: [sam] }), { status: 200 })
				: new Response('{}', { status: 403 })
		);
		vi.stubGlobal('fetch', fetchMock);
		const p = props();
		render(UnlinkPlaceDialog, p);
		await page.getByRole('button', { name: 'Remove', exact: true }).click();
		await vi.waitFor(() => expect(real(fetchMock)).toHaveLength(1));
		await expect.element(page.getByRole('button', { name: 'Remove', exact: true })).toBeEnabled();
		expect(p.onunlinked).not.toHaveBeenCalled();
	});
});
