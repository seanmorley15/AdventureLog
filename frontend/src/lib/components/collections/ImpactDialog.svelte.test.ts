import { describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import ImpactDialog from './ImpactDialog.svelte';
import { PreviewError } from '#lib/traveler-impact.js';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const sam = { uuid: 's', username: 'sam', first_name: 'Sam', last_name: '', profile_pic: null };
const preview = {
	people_released: [sam],
	includes_you: false,
	visits_deleted: 0,
	others_uploads: 0,
	places: 3
};

describe('ImpactDialog (collection delete)', () => {
	it('shows the preview in the delete confirmation and confirms once', async () => {
		const onconfirm = vi.fn(async () => true);
		const onclose = vi.fn();
		render(ImpactDialog, {
			title: 'Delete Collection',
			description: 'Delete this collection?',
			confirmLabel: 'Delete',
			danger: true,
			load: async () => preview,
			onconfirm,
			onclose
		});
		await expect.element(page.getByText('They get a copy of 3 places.')).toBeVisible();
		const del = page.getByRole('button', { name: 'Delete', exact: true });
		await expect.element(del).toBeEnabled();
		const el = (await del.element()) as HTMLButtonElement;
		el.click();
		el.click();
		await vi.waitFor(() => expect(onclose).toHaveBeenCalled());
		expect(onconfirm).toHaveBeenCalledTimes(1);
	});

	it('keeps the button off while the preview is loading', async () => {
		let release: (p: typeof preview) => void = () => {};
		render(ImpactDialog, {
			title: 'Delete Collection',
			confirmLabel: 'Delete',
			load: () => new Promise((resolve) => (release = resolve)),
			onconfirm: async () => true,
			onclose: vi.fn()
		});
		await expect.element(page.getByRole('button', { name: 'Delete', exact: true })).toBeDisabled();
		release(preview);
		await expect.element(page.getByRole('button', { name: 'Delete', exact: true })).toBeEnabled();
	});

	it("shows the server's message when the preview is refused", async () => {
		render(ImpactDialog, {
			title: 'Delete Collection',
			confirmLabel: 'Delete',
			load: async () => {
				throw new PreviewError('Request was throttled.');
			},
			onconfirm: async () => true,
			onclose: vi.fn()
		});
		await expect.element(page.getByText('Request was throttled.')).toBeVisible();
		await expect.element(page.getByRole('button', { name: 'Delete', exact: true })).toBeDisabled();
	});

	it('says the translated message, not the raw error, when the request itself fails', async () => {
		render(ImpactDialog, {
			title: 'Delete Collection',
			confirmLabel: 'Delete',
			load: async () => {
				throw new TypeError('Failed to fetch');
			},
			onconfirm: async () => true,
			onclose: vi.fn()
		});
		await expect.element(page.getByText(en.traveler_impact.preview_failed)).toBeVisible();
		expect(page.getByText('Failed to fetch').elements()).toHaveLength(0);
	});
});
