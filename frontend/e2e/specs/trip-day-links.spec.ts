import { test, expect } from '../fixtures';
import { createTrip, planSection } from '../support/trip';

/** A date `offset` days from today, typed the way the date fields expect (MM/DD/YYYY). */
function typedDate(offset: number): string {
	// "Today" is the browser's day, and the Playwright config pins the browser to
	// America/New_York. The runner is UTC, so reading its own calendar date would be a
	// day ahead for the first hours of every UTC day.
	const [month, day, year] = new Date()
		.toLocaleDateString('en-US', {
			timeZone: 'America/New_York',
			month: '2-digit',
			day: '2-digit',
			year: 'numeric'
		})
		.split('/')
		.map(Number);
	const d = new Date(Date.UTC(year, month - 1, day + offset));
	return `${String(d.getUTCMonth() + 1).padStart(2, '0')}/${String(d.getUTCDate()).padStart(2, '0')}/${d.getUTCFullYear()}`;
}

// #1346: open the itinerary on a named day, or on today while the trip is on.
test.describe('links to a day of a trip', () => {
	test('the planner opens on today and on the day a link names', async ({ page, context }) => {
		// Twelve days with today as day 8, so reaching today or day 12 needs a scroll.
		await createTrip(page, {
			name: `Long Trip ${Date.now().toString(36)}`,
			start: typedDate(-7),
			end: typedDate(4)
		});
		const tripUrl = page.url().split('?')[0];

		await page.goto(tripUrl);
		const today = planSection(page, 8);
		await expect(today.getByText('Today', { exact: true })).toBeVisible();
		await expect(today).toBeInViewport();
		await expect(planSection(page, 1).getByText('Today', { exact: true })).toHaveCount(0);

		await page.goto(`${tripUrl}?view=itinerary&day=12`);
		await expect(planSection(page, 12)).toBeInViewport();
		await expect(planSection(page, 1)).not.toBeInViewport();

		// A day's menu copies a link that opens that day.
		await context.grantPermissions(['clipboard-read', 'clipboard-write']);
		const day3 = planSection(page, 3);
		await day3.scrollIntoViewIfNeeded();
		await day3.getByRole('button', { name: 'Day actions' }).click();
		await day3.getByRole('menuitem', { name: 'Copy link to this day' }).click();
		const copied = await page.evaluate(() => navigator.clipboard.readText());
		expect(copied).toBe(`${tripUrl}?view=itinerary&day=3`);
	});
});
