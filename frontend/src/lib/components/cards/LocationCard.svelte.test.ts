import { describe, expect, it, vi } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import LocationCard from './LocationCard.svelte';

vi.mock('$app/env/public', () => ({ PUBLIC_CARTO_BASEMAP_API_KEY: '' }));
vi.mock('$app/state', () => ({ page: { data: {} } }));

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const me = { uuid: 'me', username: 'me' } as any;

function setup(role: string, createdBy: string | null) {
	const adventure: any = {
		id: 'loc1',
		name: 'Hut',
		images: [],
		visits: [],
		tags: [],
		collections: ['c1'],
		user: { uuid: 'owner', username: 'owner' },
		created_by: createdBy ? { uuid: createdBy, username: createdBy } : null
	};
	const collection: any = {
		id: 'c1',
		name: 'Alps',
		user: 'owner',
		shared_with: ['me'],
		collaborators: [{ uuid: 'me', username: 'me', is_owner: false, role }]
	};
	render(LocationCard as any, { user: me, adventure, collection });
}

describe('LocationCard Remove from the trip', () => {
	it('is offered to an editor who added the place', async () => {
		setup('editor', 'me');
		await page.getByRole('button', { name: 'Location actions' }).click();
		await expect.element(page.getByText('Remove from Alps')).toBeInTheDocument();
	});

	it("is not offered for someone else's place", async () => {
		setup('editor', 'sam');
		await page.getByRole('button', { name: 'Location actions' }).click();
		await expect.element(page.getByText('Remove from Alps')).not.toBeInTheDocument();
	});

	it('is not offered once the creator is a viewer', async () => {
		setup('viewer', 'me');
		await page.getByRole('button', { name: 'Location actions' }).click();
		await expect.element(page.getByText('Remove from Alps')).not.toBeInTheDocument();
	});
});
