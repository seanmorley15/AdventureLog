import { describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import CollectionPdfDialog from './CollectionPdfDialog.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

describe('CollectionPdfDialog', () => {
	it.each([
		['trip', 'Trip Book', 'Space to write'],
		['folder', 'Field Guide', 'Write-in space']
	] as const)('shows the %s export', async (type, title, journalLabel) => {
		render(CollectionPdfDialog, {
			collection: { id: 'c1', name: 'Sample', type },
			signedIn: true,
			onClose: vi.fn()
		});

		await expect.element(page.getByRole('heading', { name: title })).toBeVisible();
		await expect.element(page.getByText(journalLabel)).toBeVisible();
		await expect.element(page.getByRole('button', { name: 'Download PDF' })).toBeVisible();
	});

	it.each([
		['folder', true],
		['trip', false]
	] as const)('write-in space for a %s starts as %s', async (type, expected) => {
		render(CollectionPdfDialog, {
			collection: { id: 'c1', name: 'Sample', type },
			signedIn: true,
			onClose: vi.fn()
		});
		const journal = page.getByRole('checkbox').nth(1);
		if (expected) await expect.element(journal).toBeChecked();
		else await expect.element(journal).not.toBeChecked();
	});
});
