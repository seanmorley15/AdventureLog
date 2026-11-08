import { test, expect } from '../fixtures';
import { createLocationThroughWizard, openNewLocation } from '../support/locations';

// A browser whose time zone resolves to "UTC" (common on Linux, WSL, Docker and Codespaces)
// sends `timezone: "UTC"` with a new visit, and the API answers 400:
//   timezone: "UTC" is not a valid choice.
// Regression: `Visit.timezone` choices used to lack "UTC".
test.describe('browser in UTC', () => {
	test.use({ timezoneId: 'UTC' });

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
