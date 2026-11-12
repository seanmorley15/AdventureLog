import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../locales/en.json';
import Avatar from './Avatar.svelte';

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const staff = { username: 'admin', first_name: 'Ada', last_name: '', is_staff: true };

describe('Avatar menu', () => {
	// /admin is served by Django, not SvelteKit: a client-side navigation lands on a 404 (#1376).
	it('opens the admin panel with a full page load', async () => {
		render(Avatar, { user: staff });
		const link = page.getByRole('link', { name: en.navbar.admin_panel });
		await expect.element(link).toHaveAttribute('href', '/admin');
		await expect.element(link).toHaveAttribute('data-sveltekit-reload');
	});

	it('hides the admin panel from non-staff users', async () => {
		render(Avatar, { user: { ...staff, is_staff: false } });
		await expect.element(page.getByText(en.navbar.admin_panel)).not.toBeInTheDocument();
	});
});
