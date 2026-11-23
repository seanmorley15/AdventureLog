import { toLocalDatetime, toUTCDatetime } from '#lib/dateUtils.js';
import type {
	Activity,
	ActivityAnalysis,
	ActivityValueSource,
	StravaActivity
} from '#lib/types.js';

/**
 * Pure helpers behind the activity composer: turning a file analysis, an integration activity or
 * a saved activity into form state, and form state into the request. Distances, elevations and
 * speeds are held in the user's units; the API always speaks meters, seconds and m/s.
 */

export type Units = 'metric' | 'imperial';

/** Where a form value came from, by API field name. Only analyzed or imported values have one. */
export type FieldSources = Record<string, ActivityValueSource>;

export type ActivityDraft = {
	name: string;
	sportType: string;
	/** Local wall time in `timezone`, as `YYYY-MM-DDTHH:mm`. */
	startDate: string;
	timezone: string;
	trailId: string;
	distance: number | null;
	/** Seconds. */
	movingTime: number | null;
	elapsedTime: number | null;
	restTime: number | null;
	elevationGain: number | null;
	elevationLoss: number | null;
	elevHigh: number | null;
	elevLow: number | null;
	averageSpeed: number | null;
	maxSpeed: number | null;
	averageCadence: number | null;
	averageHeartRate: number | null;
	maxHeartRate: number | null;
	calories: number | null;
	startLat: number | null;
	startLng: number | null;
	endLat: number | null;
	endLng: number | null;
	externalId: string | null;
	sourceAttribution: string | null;
};

type Context = { units: Units; timezone: string };

const METERS_PER_MILE = 1609.34;
const FEET_PER_METER = 3.28084;
const MPH_PER_MS = 2.236936;
const KMH_PER_MS = 3.6;

function roundTo(value: number, digits: number) {
	const factor = 10 ** digits;
	return Math.round(value * factor) / factor;
}

export function metersToDistance(meters: number | null | undefined, units: Units) {
	if (meters == null) return null;
	return roundTo(units === 'imperial' ? meters / METERS_PER_MILE : meters / 1000, 3);
}

export function distanceToMeters(value: number | null, units: Units) {
	if (value == null) return null;
	return units === 'imperial' ? value * METERS_PER_MILE : value * 1000;
}

export function metersToElevation(meters: number | null | undefined, units: Units) {
	if (meters == null) return null;
	return roundTo(units === 'imperial' ? meters * FEET_PER_METER : meters, 0);
}

export function elevationToMeters(value: number | null, units: Units) {
	if (value == null) return null;
	return units === 'imperial' ? value / FEET_PER_METER : value;
}

export function metersPerSecondToSpeed(value: number | null | undefined, units: Units) {
	if (value == null) return null;
	return roundTo(units === 'imperial' ? value * MPH_PER_MS : value * KMH_PER_MS, 1);
}

export function speedToMetersPerSecond(value: number | null, units: Units) {
	if (value == null) return null;
	return units === 'imperial' ? value / MPH_PER_MS : value / KMH_PER_MS;
}

/**
 * Seconds in a duration the API sent: Django's `HH:MM:SS` (with `D ` days and fractions) or
 * ISO 8601 `PT1H2M3S`. `null` when it is empty or not a duration.
 */
export function parseDuration(value: string | number | null | undefined): number | null {
	if (value == null || value === '') return null;
	if (typeof value === 'number') return value;
	const iso = value.match(/^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$/);
	if (iso && value !== 'P' && value !== 'PT') {
		const [, days, hours, minutes, seconds] = iso;
		return (
			Number(days || 0) * 86400 +
			Number(hours || 0) * 3600 +
			Number(minutes || 0) * 60 +
			Math.round(Number(seconds || 0))
		);
	}
	const clock = value.match(/^(?:(\d+) )?(\d+):(\d{2}):(\d{2})(?:\.\d+)?$/);
	if (!clock) return null;
	return (
		Number(clock[1] || 0) * 86400 +
		Number(clock[2]) * 3600 +
		Number(clock[3]) * 60 +
		Number(clock[4])
	);
}

/** `1:05:09` or `5:09`, for showing a duration. */
export function formatDuration(seconds: number | null | undefined): string {
	if (seconds == null) return '';
	const total = Math.max(0, Math.round(seconds));
	const hours = Math.floor(total / 3600);
	const minutes = Math.floor((total % 3600) / 60);
	const secs = total % 60;
	const mm = hours > 0 ? String(minutes).padStart(2, '0') : String(minutes);
	return `${hours > 0 ? `${hours}:` : ''}${mm}:${String(secs).padStart(2, '0')}`;
}

export function emptyDraft(timezone: string, sportType = 'Hike'): ActivityDraft {
	return {
		name: '',
		sportType,
		startDate: '',
		timezone,
		trailId: '',
		distance: null,
		movingTime: null,
		elapsedTime: null,
		restTime: null,
		elevationGain: null,
		elevationLoss: null,
		elevHigh: null,
		elevLow: null,
		averageSpeed: null,
		maxSpeed: null,
		averageCadence: null,
		averageHeartRate: null,
		maxHeartRate: null,
		calories: null,
		startLat: null,
		startLng: null,
		endLat: null,
		endLng: null,
		externalId: null,
		sourceAttribution: null
	};
}

/**
 * Fill a draft from what a file contains. Fields the file lacks keep their current value, so
 * a draft can take a second file without losing what was typed.
 */
export function applyAnalysis(
	draft: ActivityDraft,
	analysis: ActivityAnalysis,
	{ units, timezone }: Context,
	options: { keepName?: boolean } = {}
): { draft: ActivityDraft; sources: FieldSources } {
	const v = analysis.values;
	const next: ActivityDraft = { ...draft, timezone };
	if (!options.keepName && v.name) next.name = v.name;
	if (v.sport_type) next.sportType = v.sport_type;
	if (v.start_date) next.startDate = toLocalDatetime(v.start_date, timezone);
	if (v.distance != null) next.distance = metersToDistance(v.distance, units);
	const moving = parseDuration(v.moving_time);
	const elapsed = parseDuration(v.elapsed_time);
	const rest = parseDuration(v.rest_time);
	if (moving != null) next.movingTime = moving;
	if (elapsed != null) next.elapsedTime = elapsed;
	if (rest != null) next.restTime = rest;
	if (v.elevation_gain != null) next.elevationGain = metersToElevation(v.elevation_gain, units);
	if (v.elevation_loss != null) next.elevationLoss = metersToElevation(v.elevation_loss, units);
	if (v.elev_high != null) next.elevHigh = metersToElevation(v.elev_high, units);
	if (v.elev_low != null) next.elevLow = metersToElevation(v.elev_low, units);
	if (v.average_speed != null) next.averageSpeed = metersPerSecondToSpeed(v.average_speed, units);
	if (v.max_speed != null) next.maxSpeed = metersPerSecondToSpeed(v.max_speed, units);
	if (v.average_cadence != null) next.averageCadence = roundTo(v.average_cadence, 0);
	if (v.average_heart_rate != null) next.averageHeartRate = roundTo(v.average_heart_rate, 0);
	if (v.max_heart_rate != null) next.maxHeartRate = roundTo(v.max_heart_rate, 0);
	if (v.calories != null) next.calories = roundTo(v.calories, 0);
	if (v.start_lat != null) next.startLat = v.start_lat;
	if (v.start_lng != null) next.startLng = v.start_lng;
	if (v.end_lat != null) next.endLat = v.end_lat;
	if (v.end_lng != null) next.endLng = v.end_lng;
	return { draft: next, sources: { ...analysis.sources } };
}

/**
 * Lay a Strava or Endurain activity's own totals over a draft. The provider's figures win,
 * because they come from the recording device; the draft keeps whatever it does not report.
 */
export function applyProviderActivity(
	draft: ActivityDraft,
	sources: FieldSources,
	activity: StravaActivity,
	{ units, timezone }: Context
): { draft: ActivityDraft; sources: FieldSources } {
	const next: ActivityDraft = { ...draft };
	const marked: FieldSources = { ...sources };
	const take = <K extends keyof ActivityDraft>(
		field: K,
		value: ActivityDraft[K] | null | undefined,
		apiField: string
	) => {
		if (value == null || (typeof value === 'number' && value === 0)) return;
		next[field] = value as ActivityDraft[K];
		marked[apiField] = 'device';
	};

	next.timezone = activity.timezone || timezone;
	if (activity.name) next.name = activity.name;
	if (activity.sport_type) next.sportType = activity.sport_type;
	if (activity.start_date) next.startDate = toLocalDatetime(activity.start_date, next.timezone);
	take('distance', metersToDistance(activity.distance, units), 'distance');
	take('movingTime', activity.moving_time, 'moving_time');
	take('elapsedTime', activity.elapsed_time, 'elapsed_time');
	take('restTime', activity.rest_time, 'rest_time');
	take('elevationGain', metersToElevation(activity.total_elevation_gain, units), 'elevation_gain');
	take('elevationLoss', metersToElevation(activity.elevation_loss, units), 'elevation_loss');
	take('elevHigh', metersToElevation(activity.elev_high, units), 'elev_high');
	take('elevLow', metersToElevation(activity.elev_low, units), 'elev_low');
	take('averageSpeed', metersPerSecondToSpeed(activity.average_speed, units), 'average_speed');
	take('maxSpeed', metersPerSecondToSpeed(activity.max_speed, units), 'max_speed');
	take('averageCadence', activity.average_cadence, 'average_cadence');
	take('calories', activity.calories, 'calories');
	if (activity.start_latlng) {
		next.startLat = activity.start_latlng[0];
		next.startLng = activity.start_latlng[1];
	}
	if (activity.end_latlng) {
		next.endLat = activity.end_latlng[0];
		next.endLng = activity.end_latlng[1];
	}
	next.externalId = String(activity.id);
	next.sourceAttribution = activity.garmin_attribution ?? null;
	return { draft: next, sources: marked };
}

/** A saved activity as form state, for editing. */
export function draftFromActivity(activity: Activity, { units, timezone }: Context): ActivityDraft {
	const zone = activity.timezone || timezone;
	return {
		name: activity.name,
		sportType: activity.sport_type || 'General',
		startDate: activity.start_date ? toLocalDatetime(activity.start_date, zone) : '',
		timezone: zone,
		trailId: activity.trail ?? '',
		distance: metersToDistance(activity.distance, units),
		movingTime: parseDuration(activity.moving_time),
		elapsedTime: parseDuration(activity.elapsed_time),
		restTime: parseDuration(activity.rest_time),
		elevationGain: metersToElevation(activity.elevation_gain, units),
		elevationLoss: metersToElevation(activity.elevation_loss, units),
		elevHigh: metersToElevation(activity.elev_high, units),
		elevLow: metersToElevation(activity.elev_low, units),
		averageSpeed: metersPerSecondToSpeed(activity.average_speed, units),
		maxSpeed: metersPerSecondToSpeed(activity.max_speed, units),
		averageCadence: activity.average_cadence,
		averageHeartRate: activity.average_heart_rate,
		maxHeartRate: activity.max_heart_rate,
		calories: activity.calories,
		startLat: activity.start_lat,
		startLng: activity.start_lng,
		endLat: activity.end_lat,
		endLng: activity.end_lng,
		externalId: activity.external_service_id,
		sourceAttribution: activity.source_attribution ?? null
	};
}

/** "Morning Hike": the part of the day (from the local start time) and the sport. */
export function defaultActivityName(
	sportLabel: string,
	startDate: string,
	translate: (key: string, values?: Record<string, string>) => string
): string {
	const hour = startDate ? Number(startDate.slice(11, 13)) : NaN;
	if (Number.isNaN(hour)) return sportLabel;
	const period =
		hour < 5
			? 'night'
			: hour < 12
				? 'morning'
				: hour < 17
					? 'afternoon'
					: hour < 21
						? 'evening'
						: 'night';
	return translate('activities.default_name', {
		period: translate(`activities.period_${period}`),
		sport: sportLabel
	});
}

type RequestOptions = {
	units: Units;
	visitId?: string | null;
	dayId?: string | null;
	collectionId?: string | null;
	file?: File | null;
	/** Editing: send `''` for a cleared number so the API empties it. */
	clearEmpty?: boolean;
};

/** The multipart body the activity endpoint takes. */
export function draftToFormData(draft: ActivityDraft, options: RequestOptions): FormData {
	const { units, file, clearEmpty = false } = options;
	const form = new FormData();
	const put = (name: string, value: string | number | null | undefined) => {
		if (value == null || value === '') {
			if (clearEmpty) form.append(name, '');
			return;
		}
		form.append(name, String(value));
	};

	if (options.visitId) form.append('visit', options.visitId);
	if (options.dayId) form.append('day', options.dayId);
	if (options.collectionId) form.append('collection', options.collectionId);
	form.append('name', draft.name.trim());
	form.append('sport_type', draft.sportType);
	put('trail', draft.trailId);
	if (draft.timezone) form.append('timezone', draft.timezone);
	if (draft.startDate) {
		const utc = toUTCDatetime(draft.startDate, draft.timezone);
		if (utc) form.append('start_date', utc);
		// The wall-clock time, labelled UTC, the way Strava reports `start_date_local`.
		form.append('start_date_local', `${draft.startDate}:00Z`);
	} else if (clearEmpty) {
		form.append('start_date', '');
	}
	const duration = (seconds: number | null) =>
		seconds == null ? null : `PT${Math.round(seconds)}S`;
	put('distance', distanceToMeters(draft.distance, units));
	put('moving_time', duration(draft.movingTime));
	put('elapsed_time', duration(draft.elapsedTime));
	put('rest_time', duration(draft.restTime));
	put('elevation_gain', elevationToMeters(draft.elevationGain, units));
	put('elevation_loss', elevationToMeters(draft.elevationLoss, units));
	put('elev_high', elevationToMeters(draft.elevHigh, units));
	put('elev_low', elevationToMeters(draft.elevLow, units));
	put('average_speed', speedToMetersPerSecond(draft.averageSpeed, units));
	put('max_speed', speedToMetersPerSecond(draft.maxSpeed, units));
	put('average_cadence', draft.averageCadence);
	put('average_heart_rate', draft.averageHeartRate);
	put('max_heart_rate', draft.maxHeartRate);
	put('calories', draft.calories);
	// A point needs both coordinates, so a half-filled one is left out rather than rejected.
	if (draft.startLat != null && draft.startLng != null) {
		form.append('start_lat', String(draft.startLat));
		form.append('start_lng', String(draft.startLng));
	}
	if (draft.endLat != null && draft.endLng != null) {
		form.append('end_lat', String(draft.endLat));
		form.append('end_lng', String(draft.endLng));
	}
	if (draft.externalId) form.append('external_service_id', draft.externalId);
	if (draft.sourceAttribution) form.append('source_attribution', draft.sourceAttribution);
	if (file) form.append('gpx_file', file);
	return form;
}

export type ProfilePoint = { distance: number; elevation: number };

const EARTH_RADIUS_M = 6371008.8;
const MAX_PROFILE_POINTS = 400;

function haversine(a: number[], b: number[]) {
	const toRad = (degrees: number) => (degrees * Math.PI) / 180;
	const dLat = toRad(b[1] - a[1]);
	const dLon = toRad(b[0] - a[0]);
	const h =
		Math.sin(dLat / 2) ** 2 +
		Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLon / 2) ** 2;
	return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

/**
 * Elevation against distance along the track, from GeoJSON whose coordinates are
 * `[lon, lat, ele]`. Distance is in meters and runs across all of a file's segments. Empty
 * when the track has no elevation.
 */
export function elevationProfile(geojson: any): ProfilePoint[] {
	const lines: number[][][] = (geojson?.features ?? [])
		.filter((feature: any) => feature?.geometry?.type === 'LineString')
		.map((feature: any) => feature.geometry.coordinates);
	const points: ProfilePoint[] = [];
	let distance = 0;
	for (const line of lines) {
		line.forEach((coordinate, index) => {
			if (index > 0) distance += haversine(line[index - 1], coordinate);
			if (coordinate.length >= 3 && Number.isFinite(coordinate[2])) {
				points.push({ distance, elevation: coordinate[2] });
			}
		});
	}
	if (points.length <= MAX_PROFILE_POINTS) return points;
	const step = (points.length - 1) / (MAX_PROFILE_POINTS - 1);
	return Array.from({ length: MAX_PROFILE_POINTS }, (_, i) => points[Math.round(i * step)]);
}

/** Every `[lon, lat]` in the GeoJSON's lines, for fitting a map to the track. */
export function trackBounds(geojson: any): [number, number][] {
	const corners: [number, number][] = [];
	for (const feature of geojson?.features ?? []) {
		if (feature?.geometry?.type !== 'LineString') continue;
		for (const [lon, lat] of feature.geometry.coordinates) corners.push([lon, lat]);
	}
	return corners;
}
