import { expect, type Page } from '@playwright/test';

export type Credentials = {
	username: string;
	email: string;
	password: string;
	firstName: string;
	lastName: string;
};

// Unique per process so reruns against the same long-lived stack never collide.
const RUN_ID = Date.now().toString(36);
let counter = 0;

/** Fresh credentials. `label` shows up in the username to make failures easier to trace. */
export function newCredentials(label = 'user'): Credentials {
	const suffix = `${label}${RUN_ID}x${++counter}${process.pid}`
		.toLowerCase()
		.replace(/[^a-z0-9]/g, '');
	return {
		username: suffix.slice(0, 30),
		email: `${suffix}@example.test`,
		password: 'Correct-Horse-9-Battery',
		firstName: 'E2E',
		lastName: label.charAt(0).toUpperCase() + label.slice(1)
	};
}

/** Create an account through the real signup page and land on the app, signed in. */
export async function signUp(page: Page, creds: Credentials) {
	await page.goto('/signup');
	await page.locator('input[name="username"]').fill(creds.username);
	await page.locator('input[name="email"]').fill(creds.email);
	await page.locator('input[name="first_name"]').fill(creds.firstName);
	await page.locator('input[name="last_name"]').fill(creds.lastName);
	await page.locator('input[name="password1"]').fill(creds.password);
	await page.locator('input[name="password2"]').fill(creds.password);
	const terms = page.locator('input[name="accept_terms"]');
	if (await terms.count()) await terms.check();
	await page.locator('form button[type="submit"]').click();
	await expect(page).not.toHaveURL(/\/signup/);
}

export async function logIn(page: Page, creds: Pick<Credentials, 'username' | 'password'>) {
	await page.goto('/login');
	await page.locator('input[name="username"]').fill(creds.username);
	await page.locator('input[name="password"]').fill(creds.password);
	await page.locator('form button[type="submit"]').click();
	await expect(page).not.toHaveURL(/\/login/);
}
