/**
 * Translation keys that were already missing from locales/en.json when the locale test was
 * added. Each one shows users the raw key (for example "categories.no_categories_yet") instead
 * of text. Fix one by adding it to en.json and deleting it here: the locale unit test fails
 * until you do, so this list can only shrink. The E2E broken-UI guard also tolerates these.
 */
export const KNOWN_MISSING_KEYS = [
	'adventures.error_occurred',
	'adventures.failed_to_fetch_activities',
	'adventures.found_activities',
	'adventures.no_strava_activities_found',
	'adventures.strava_not_connected',
	'adventures.transport_end',
	'adventures.transport_start',
	'billing.alert_trial_active_description',
	'categories.no_categories_yet',
	'common.refresh',
	'invites.fetch_failed',
	'map.hide_image_pins',
	'map.show_image_pins'
];
