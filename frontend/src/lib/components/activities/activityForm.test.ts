import { describe, expect, it } from 'vitest';
import {
	applyAnalysis,
	applyProviderActivity,
	draftFromActivity,
	draftToFormData,
	defaultActivityName,
	elevationProfile,
	emptyDraft,
	formatDuration,
	parseDuration
} from './activityForm.js';
import type { Activity, ActivityAnalysis, StravaActivity } from '#lib/types.js';

const analysis: ActivityAnalysis = {
	values: {
		name: 'Morning Hike',
		sport_type: 'Hike',
		distance: 10000,
		moving_time: '01:00:00',
		elapsed_time: '01:10:00',
		rest_time: '00:10:00',
		elevation_gain: 300,
		start_date: '2026-06-06T08:00:00Z',
		average_speed: 2.5,
		average_heart_rate: 141.6,
		start_lat: 41,
		start_lng: 2
	},
	sources: { distance: 'computed', elevation_gain: 'device' },
	format: 'fit',
	point_count: 100,
	has_timestamps: true,
	has_elevation: true,
	utc_offset_minutes: null,
	warnings: [],
	geojson: null
};
const metric = { units: 'metric' as const, timezone: 'Europe/Madrid' };

describe('parseDuration', () => {
	it('reads Django clock durations, with days and fractions', () => {
		expect(parseDuration('01:02:03')).toBe(3723);
		expect(parseDuration('1 02:00:00')).toBe(93600);
		expect(parseDuration('00:00:05.250000')).toBe(5);
	});
	it('reads ISO 8601 durations', () => {
		expect(parseDuration('PT1H2M3S')).toBe(3723);
		expect(parseDuration('PT90S')).toBe(90);
	});
	it('is null for anything else, so 25 is not read as 25 seconds', () => {
		expect(parseDuration('25')).toBeNull();
		expect(parseDuration('')).toBeNull();
		expect(parseDuration(null)).toBeNull();
		expect(parseDuration('PT')).toBeNull();
	});
});

describe('formatDuration', () => {
	it('shows hours only when there are some', () => {
		expect(formatDuration(3723)).toBe('1:02:03');
		expect(formatDuration(309)).toBe('5:09');
		expect(formatDuration(null)).toBe('');
	});
});

describe('applyAnalysis', () => {
	it('fills the draft in the display units, with the start in the local timezone', () => {
		const { draft, sources } = applyAnalysis(emptyDraft('Europe/Madrid'), analysis, metric);
		expect(draft).toMatchObject({
			name: 'Morning Hike',
			distance: 10,
			movingTime: 3600,
			restTime: 600,
			elevationGain: 300,
			averageSpeed: 9,
			averageHeartRate: 142,
			startDate: '2026-06-06T10:00'
		});
		expect(sources.elevation_gain).toBe('device');
	});
	it('converts to miles, feet and mph', () => {
		const { draft } = applyAnalysis(emptyDraft('UTC'), analysis, {
			units: 'imperial',
			timezone: 'UTC'
		});
		expect(draft.distance).toBeCloseTo(6.214, 3);
		expect(draft.elevationGain).toBe(984);
		expect(draft.averageSpeed).toBe(5.6);
	});
	it('keeps what the file lacks and, when asked, the typed name', () => {
		const typed = { ...emptyDraft('UTC'), name: 'My name', calories: 99 };
		const { draft } = applyAnalysis(typed, analysis, metric, { keepName: true });
		expect(draft.name).toBe('My name');
		expect(draft.calories).toBe(99);
	});
});

describe('applyProviderActivity', () => {
	const strava = {
		id: 7,
		name: 'Lunch ride',
		sport_type: 'Ride',
		distance: 25000,
		moving_time: 3000,
		elapsed_time: 3300,
		rest_time: 300,
		total_elevation_gain: 410,
		elevation_loss: null,
		elev_high: 0,
		elev_low: 0,
		average_speed: 8.3,
		max_speed: 12,
		average_cadence: null,
		calories: 0,
		start_date: '2026-06-06T10:00:00Z',
		timezone: 'Europe/Madrid',
		garmin_attribution: 'Garmin Edge 840'
	} as unknown as StravaActivity;

	it("lets the provider's totals win and marks them as from the device", () => {
		const base = applyAnalysis(emptyDraft('UTC'), analysis, metric);
		const { draft, sources } = applyProviderActivity(base.draft, base.sources, strava, metric);
		expect(draft.distance).toBe(25);
		expect(draft.elevationGain).toBe(410);
		expect(draft.externalId).toBe('7');
		expect(draft.sourceAttribution).toBe('Garmin Edge 840');
		expect(sources.distance).toBe('device');
	});
	it('does not wipe what the file measured when the provider reports nothing', () => {
		const base = applyAnalysis(emptyDraft('UTC'), analysis, metric);
		const { draft } = applyProviderActivity(base.draft, base.sources, strava, metric);
		expect(draft.elevHigh).toBe(base.draft.elevHigh);
		expect(draft.averageHeartRate).toBe(142);
		expect(draft.calories).toBeNull();
	});
});

describe('draftToFormData', () => {
	const draft = {
		...applyAnalysis(emptyDraft('Europe/Madrid'), analysis, metric).draft,
		trailId: ''
	};

	it('sends meters, seconds, UTC and the parent', () => {
		const form = draftToFormData(draft, { units: 'metric', dayId: 'day-1' });
		expect(form.get('day')).toBe('day-1');
		expect(form.get('visit')).toBeNull();
		expect(form.get('distance')).toBe('10000');
		expect(form.get('moving_time')).toBe('PT3600S');
		expect(form.get('start_date')).toBe('2026-06-06T08:00:00Z');
		expect(form.get('start_date_local')).toBe('2026-06-06T10:00:00Z');
		expect(form.get('elevation_loss')).toBeNull();
	});
	it('converts imperial values back to meters', () => {
		const imperial = applyAnalysis(emptyDraft('UTC'), analysis, {
			units: 'imperial',
			timezone: 'UTC'
		}).draft;
		const form = draftToFormData(imperial, { units: 'imperial', visitId: 'v' });
		expect(Number(form.get('distance'))).toBeCloseTo(10000, -1);
		expect(Number(form.get('elevation_gain'))).toBeCloseTo(300, -1);
	});
	it('sends empty numbers as blanks when editing, so they can be cleared', () => {
		const form = draftToFormData(draft, { units: 'metric', visitId: 'v', clearEmpty: true });
		expect(form.get('elevation_loss')).toBe('');
	});
	it('leaves out a half-filled point and attaches the file', () => {
		const file = new File(['x'], 'ride.fit');
		const form = draftToFormData(
			{ ...draft, endLat: 1, endLng: null },
			{ units: 'metric', visitId: 'v', file }
		);
		expect(form.get('end_lat')).toBeNull();
		expect(form.get('start_lat')).toBe('41');
		expect(form.get('gpx_file')).toBe(file);
	});
});

describe('draftFromActivity', () => {
	it('turns a saved activity into editable state', () => {
		const activity = {
			name: 'Old',
			sport_type: 'Run',
			distance: 5000,
			moving_time: '00:25:00',
			start_date: '2026-06-06T08:00:00Z',
			timezone: 'UTC',
			trail: null,
			average_heart_rate: 150
		} as unknown as Activity;
		const draft = draftFromActivity(activity, metric);
		expect(draft).toMatchObject({
			distance: 5,
			movingTime: 1500,
			startDate: '2026-06-06T08:00',
			averageHeartRate: 150
		});
	});
});

describe('defaultActivityName', () => {
	const translate = (key: string, values?: Record<string, string>) =>
		values ? `${values.period} ${values.sport}` : key.replace('activities.period_', '');
	it('names it for the part of the day', () => {
		expect(defaultActivityName('Hike', '2026-06-06T07:30', translate)).toBe('morning Hike');
		expect(defaultActivityName('Run', '2026-06-06T18:00', translate)).toBe('evening Run');
	});
	it('falls back to the sport when the start is unknown', () => {
		expect(defaultActivityName('Hike', '', translate)).toBe('Hike');
	});
});

describe('elevationProfile', () => {
	const geojson = {
		features: [
			{
				geometry: {
					type: 'LineString',
					coordinates: [
						[2, 41, 100],
						[2, 41.001, 110],
						[2, 41.002, 105]
					]
				}
			}
		]
	};
	it('accumulates distance along the track', () => {
		const profile = elevationProfile(geojson);
		expect(profile).toHaveLength(3);
		expect(profile[2].distance).toBeCloseTo(222, 0);
		expect(profile[1].elevation).toBe(110);
	});
	it('is empty without elevation', () => {
		expect(
			elevationProfile({
				features: [
					{
						geometry: {
							type: 'LineString',
							coordinates: [
								[2, 41],
								[2, 42]
							]
						}
					}
				]
			})
		).toEqual([]);
		expect(elevationProfile(null)).toEqual([]);
	});
	it('is capped so a long recording stays cheap to draw', () => {
		const coordinates = Array.from({ length: 5000 }, (_, i) => [2, 41 + i * 1e-5, 100 + (i % 7)]);
		expect(
			elevationProfile({ features: [{ geometry: { type: 'LineString', coordinates } }] }).length
		).toBeLessThanOrEqual(400);
	});
});
