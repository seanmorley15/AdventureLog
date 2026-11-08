import { test, expect } from '../fixtures';
import { createLocationThroughWizard, openNewLocation } from '../support/locations';

// A browser whose time zone resolves to "UTC" (common on Linux, WSL, Docker and Codespaces)
// sends `timezone: "UTC"` with a new visit, and the API answers 400:
//   timezone: "UTC" is not a valid choice.
// `Visit.timezone` takes its choices from core/timezones.py TIMEZONES, which has no "UTC",
// even though that module's own validator accepts it.
//
// `test.fail()` keeps the suite green while the bug exists and turns this test red the day
// it is fixed, as a reminder to delete the line below.
test.describe('browser in UTC', () => {
	test.use({ timezoneId: 'UTC' });
	test.fail();

	test('a visit can be added', async ({ page }) => {
		const dialog = await openNewLocation(page);
		await createLocationThroughWizard(page, dialog, {
			name: 'UTC Visit Test',
			category: 'Landmark',
			visit: { start: '06/12/2027' }
		});
		await expect(page.getByText('UTC Visit Test').first()).toBeVisible();
	});
});
