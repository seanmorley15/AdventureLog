import { test as base, expect, type APIRequestContext, type Page } from '@playwright/test';

export type Category = { id: string; name: string; display_name: string; icon: string };

/**
 * Seeds and cleans up data through the SvelteKit `/api` proxy, which forwards the
 * browser session and handles CSRF, so tests never talk to Django directly.
 * Everything created here, or registered with `trackLocation`, is deleted when the
 * test ends.
 */
export class Api {
	private readonly locations: string[] = [];
	private readonly categories: string[] = [];

	constructor(private readonly request: APIRequestContext) {}

	async createCategory(displayName: string, icon = '🧪'): Promise<Category> {
		const res = await this.request.post('/api/categories', {
			data: {
				name: displayName.toLowerCase().replace(/\s+/g, '_'),
				display_name: displayName,
				icon
			}
		});
		expect(res.ok(), `POST /api/categories returned ${res.status()}`).toBeTruthy();
		const category = (await res.json()) as Category;
		this.categories.push(category.id);
		return category;
	}

	/** Register a location created through the UI so it is removed after the test. */
	trackLocation(id: string) {
		this.locations.push(id);
	}

	async cleanup() {
		for (const id of this.locations.splice(0)) {
			await this.request.delete(`/api/locations/${id}`);
		}
		for (const id of this.categories.splice(0)) {
			await this.request.delete(`/api/categories/${id}`);
		}
	}
}

export const test = base.extend<{ api: Api }>({
	context: async ({ context, baseURL }, use) => {
		// Keep tests off the public internet: map tiles, flag CDN, emoji data and so on.
		const origin = new URL(baseURL ?? 'http://localhost').origin;
		await context.route(
			(url) => url.origin !== origin,
			(route) => route.abort('blockedbyclient')
		);
		await use(context);
	},
	api: async ({ page }, use) => {
		const api = new Api(page.request);
		await use(api);
		await api.cleanup();
	}
});

export { expect };

/**
 * Fill and submit the login form. Scoped to the form because the navbar has its own
 * Login button on the login page.
 */
export async function submitLogin(page: Page, username: string, password: string) {
	const form = page.locator('form', { has: page.getByLabel('Username') });
	await form.getByLabel('Username').fill(username);
	await form.getByLabel('Password').fill(password);
	await form.getByRole('button', { name: 'Login' }).click();
}
