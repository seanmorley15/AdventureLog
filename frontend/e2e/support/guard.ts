import type { Page } from '@playwright/test';

/**
 * Console noise that is known to be harmless. Keep this list short and explain every entry:
 * an allowlist that grows silently defeats the point of the guard.
 */
const IGNORED_CONSOLE_ERRORS: RegExp[] = [
	// Requests for third-party hosts are blocked on purpose by stubExternalNetwork().
	/Failed to load resource: net::ERR_FAILED/,
	/net::ERR_BLOCKED_BY_CLIENT/,
	// The Visits step asks for Strava activities even when Strava isn't connected, and the
	// 404 "not connected" answer is logged by Chrome as a console error. It is not user-visible,
	// but the app could skip the request when the integration is off.
	/status of 404.*\/api\/integrations\/strava\/activities/,
	// The Transportation form does the same probe and console.errors the "not connected" answer
	// (with the untranslated key adventures.strava_not_connected, see known-missing-keys.ts).
	/Error fetching Strava activities/
];

export type GuardIssue = { kind: 'pageerror' | 'console' | 'http'; detail: string };

/**
 * Collects the symptoms of a broken UI while a test runs: uncaught exceptions, console errors
 * and 5xx responses from the API. Call `issues()` at the end of a test (the shared fixture does).
 */
export function watchForBrokenUI(page: Page) {
	const found: GuardIssue[] = [];

	page.on('pageerror', (error) => {
		found.push({ kind: 'pageerror', detail: `${error.name}: ${error.message}` });
	});

	page.on('console', (message) => {
		if (message.type() !== 'error') return;
		// Chrome reports failed requests as "Failed to load resource: ... status of 404" and puts
		// the URL in the message location, so match the allowlist against both together.
		const detail = `${message.text()} (${message.location().url})`;
		if (IGNORED_CONSOLE_ERRORS.some((pattern) => pattern.test(detail))) return;
		found.push({ kind: 'console', detail });
	});

	page.on('response', (response) => {
		const url = new URL(response.url());
		if (!url.pathname.startsWith('/api/')) return;
		if (response.status() < 500) return;
		found.push({
			kind: 'http',
			detail: `${response.request().method()} ${url.pathname} -> ${response.status()}`
		});
	});

	return {
		issues: () => found.slice(),
		/** Forget what was seen so far, for tests that deliberately provoke an error. */
		clear: () => {
			found.length = 0;
		}
	};
}
