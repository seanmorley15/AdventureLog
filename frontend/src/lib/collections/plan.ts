import { apiErrorMessage } from '#lib/api/index.js';
import type {
	Checklist,
	Collection,
	CollectionItineraryDay,
	CollectionItineraryItem,
	Location,
	Lodging,
	Note,
	Transportation
} from '#lib/types.js';

export type PlanObjectType = 'location' | 'lodging' | 'transportation' | 'note' | 'checklist';
export type PlanObject = Location | Lodging | Transportation | Note | Checklist;

/** One planner row. `item` is null for a linked object that has no placement yet. */
export type PlanRow = {
	id: string;
	item: CollectionItineraryItem | null;
	type: PlanObjectType | null;
	objectId: string;
	object: PlanObject | null;
};

export type LogVisitResult = 'ok' | 'date_required' | 'error';

export type PlacementPayload = {
	day_index: number | null;
	is_global: boolean;
	span_end_index: number | null;
	is_optional: boolean;
	start_time: string | null;
	end_time: string | null;
};

export const SPAN_TYPES: PlanObjectType[] = ['lodging', 'transportation', 'location'];
export const GLOBAL_TYPES: PlanObjectType[] = ['note', 'checklist'];

const TYPE_ALIASES: Record<string, PlanObjectType> = {
	visit: 'location',
	location: 'location',
	lodging: 'lodging',
	transportation: 'transportation',
	note: 'note',
	checklist: 'checklist'
};

function isTypeName(value: unknown): value is string {
	return typeof value === 'string' && value.length > 0 && !/^\d+$/.test(value);
}

export function placementType(item: CollectionItineraryItem): PlanObjectType | null {
	const raw = [item.content_type, item.object_name, item.item?.type].find(isTypeName) || '';
	return TYPE_ALIASES[raw] ?? null;
}

export function objectsOfType(collection: Collection, type: PlanObjectType): PlanObject[] {
	switch (type) {
		case 'location':
			return collection.locations ?? [];
		case 'lodging':
			return collection.lodging ?? [];
		case 'transportation':
			return collection.transportations ?? [];
		case 'note':
			return collection.notes ?? [];
		case 'checklist':
			return collection.checklists ?? [];
	}
}

export function findObject(
	collection: Collection,
	type: PlanObjectType | null,
	id: string
): PlanObject | null {
	if (!type) return null;
	return objectsOfType(collection, type).find((obj) => String(obj.id) === String(id)) ?? null;
}

export function indexedDays(collection: Collection): CollectionItineraryDay[] {
	return (collection.itinerary_days ?? [])
		.filter((day) => day.index != null)
		.sort((a, b) => (a.index ?? 0) - (b.index ?? 0));
}

/** Every trip is planned by days. Folders are not. */
export function showsDayPlanner(collection: Collection): boolean {
	return collection.type === 'trip';
}

export type PlanPin = {
	type: PlanObjectType;
	objectId: string;
	dayIndex: number | null;
	spanEnd: number | null;
	optional: boolean;
	ideas: boolean;
	visited: boolean;
	visitId: string | null;
};

const PIN_TYPES = new Set<PlanObjectType>(['location', 'lodging', 'transportation']);

export const DAY_PIN_COLORS = [
	'#0ea5e9',
	'#10b981',
	'#f59e0b',
	'#8b5cf6',
	'#f43f5e',
	'#06b6d4',
	'#f97316',
	'#6366f1'
];

export function dayPinColor(index: number): string {
	return DAY_PIN_COLORS[(Math.max(index, 1) - 1) % DAY_PIN_COLORS.length];
}

export function pinCoversDay(pin: PlanPin, day: number): boolean {
	if (pin.dayIndex == null) return false;
	const end = pin.spanEnd ?? pin.dayIndex;
	return pin.dayIndex <= day && day <= end;
}

/** One entry per placement that can be a pin. A span is a single entry. */
export function planPins(collection: Collection): PlanPin[] {
	const pins: PlanPin[] = [];
	for (const item of collection.itinerary ?? []) {
		const type = placementType(item);
		if (!type || !PIN_TYPES.has(type)) continue;
		const ideas = !item.day && !item.is_global;
		const visitId =
			type === 'location' ? recordedVisitId(collection, item) : (item.logged_visit ?? null);
		pins.push({
			type,
			objectId: String(item.object_id),
			dayIndex: item.day_index ?? null,
			spanEnd: item.span_end_index ?? item.day_index ?? null,
			optional: Boolean(item.is_optional),
			ideas,
			visited: Boolean(visitId),
			visitId
		});
	}
	return pins;
}

function lngLat(latitude: unknown, longitude: unknown): [number, number] | null {
	const lat = typeof latitude === 'number' ? latitude : Number(latitude);
	const lon = typeof longitude === 'number' ? longitude : Number(longitude);
	if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
	return [lon, lat];
}

function samePoint(a: [number, number], b: [number, number]): boolean {
	return Math.abs(a[0] - b[0]) < 1e-6 && Math.abs(a[1] - b[1]) < 1e-6;
}

/**
 * Map points for one day's stops, in plan order. Stays that started on an
 * earlier day come first, then this day's items. A transport contributes its
 * origin and then its destination.
 */
export function dayStopPath(collection: Collection, day: number): [number, number][] {
	const items = (collection.itinerary ?? []).filter((item) => {
		const type = placementType(item);
		if (!type || !PIN_TYPES.has(type) || item.day_index == null) return false;
		const end = item.span_end_index ?? item.day_index;
		return item.day_index <= day && day <= end;
	});
	items.sort((a, b) => {
		const aStart = a.day_index ?? day;
		const bStart = b.day_index ?? day;
		const aContinued = aStart < day ? 0 : 1;
		const bContinued = bStart < day ? 0 : 1;
		if (aContinued !== bContinued) return aContinued - bContinued;
		if (aContinued === 0 && aStart !== bStart) return aStart - bStart;
		return a.order - b.order;
	});

	const points: [number, number][] = [];
	for (const item of items) {
		const type = placementType(item);
		if (!type) continue;
		const obj = findObject(collection, type, String(item.object_id));
		if (!obj) continue;
		const next: [number, number][] = [];
		if (type === 'transportation') {
			const transport = obj as Transportation;
			const origin = lngLat(transport.origin_latitude, transport.origin_longitude);
			const destination = lngLat(transport.destination_latitude, transport.destination_longitude);
			if (origin) next.push(origin);
			if (destination && (!origin || !samePoint(origin, destination))) next.push(destination);
		} else {
			const place = obj as Location | Lodging;
			const point = lngLat(place.latitude, place.longitude);
			if (point) next.push(point);
		}
		for (const point of next) {
			const last = points[points.length - 1];
			if (!last || !samePoint(last, point)) points.push(point);
		}
	}
	return points;
}

/** The dates a placement covers, from its projected start through a span. */
export function placementRange(
	item: CollectionItineraryItem
): { start: string; end: string } | null {
	const start = dateOnly(item.date);
	if (!start || item.day_index == null) return null;
	const extra =
		item.span_end_index != null && item.span_end_index > item.day_index
			? item.span_end_index - item.day_index
			: 0;
	return { start, end: addDays(start, extra) };
}

/**
 * A visit already written for this stop, either by Log visit or earlier on the
 * same dates. A visit on a different day does not count.
 */
export function recordedVisitId(
	collection: Collection,
	item: CollectionItineraryItem | null | undefined
): string | null {
	if (!item) return null;
	if (item.logged_visit) return item.logged_visit;
	const range = placementRange(item);
	if (!range) return null;
	const location = (collection.locations ?? []).find(
		(entry) => String(entry.id) === String(item.object_id)
	);
	let match: { id: string; start: string } | null = null;
	for (const visit of location?.visits ?? []) {
		const start = dateOnly(visit.start_date);
		const end = dateOnly(visit.end_date) || start;
		if (!start || !end || start > range.end || end < range.start) continue;
		if (!match || start < match.start) match = { id: visit.id, start };
	}
	return match?.id ?? null;
}

/** HH:MM from an API time (HH:MM:SS) or an empty string. */
export function clockValue(value: string | null | undefined): string {
	return value ? value.slice(0, 5) : '';
}

export function dateOnly(value: string | null | undefined): string | null {
	if (!value) return null;
	return value.split('T')[0];
}

/** Whole days between two date-only strings, `to - from`. */
export function daysBetween(from: string | null, to: string | null): number {
	if (!from || !to) return 0;
	const a = Date.parse(`${from}T00:00:00Z`);
	const b = Date.parse(`${to}T00:00:00Z`);
	if (Number.isNaN(a) || Number.isNaN(b)) return 0;
	return Math.round((b - a) / 86_400_000);
}

export function addDays(iso: string, days: number): string {
	const base = new Date(`${iso}T00:00:00Z`);
	base.setUTCDate(base.getUTCDate() + days);
	return base.toISOString().slice(0, 10);
}

/**
 * The last day a new lodging or transport record covers when it is saved from
 * a day, so the placement span matches the nights or arrival the user entered.
 */
export function spanEndFromRecord(
	type: PlanObjectType,
	record: PlanObject,
	startIndex: number,
	dayCount: number
): number | null {
	let extra = 0;
	if (type === 'lodging') {
		const lodging = record as Lodging;
		extra = daysBetween(dateOnly(lodging.check_in), dateOnly(lodging.check_out)) - 1;
	} else if (type === 'transportation') {
		const transport = record as Transportation;
		extra = daysBetween(dateOnly(transport.date), dateOnly(transport.end_date));
	}
	if (extra <= 0) return null;
	return Math.min(startIndex + extra, dayCount);
}

export function browserTimezone(): string | undefined {
	try {
		return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
	} catch {
		return undefined;
	}
}

export type PlanError = {
	error?: string;
	code?: string;
	item_count?: number;
	day_indexes?: number[];
};

export type PlanResponse<T = any> = {
	ok: boolean;
	status: number;
	data: T & PlanError;
};

export async function planRequest<T = any>(
	url: string,
	method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
	body?: unknown
): Promise<PlanResponse<T>> {
	const res = await fetch(url, {
		method,
		headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	let data: any = null;
	if (res.status !== 204) {
		data = await res.json().catch(() => null);
	}
	return { ok: res.ok, status: res.status, data };
}

/** The message to show for a failed plan request. */
export const errorMessage = apiErrorMessage;

/** A fingerprint of the stored plan, used to notice changes made by someone else. */
export function planFingerprint(collection: Collection): string {
	const items = (collection.itinerary ?? [])
		.map((item) => `${item.id}:${item.updated_at ?? ''}`)
		.sort()
		.join('|');
	const days = indexedDays(collection)
		.map((day) => `${day.id}:${day.index}:${day.updated_at}`)
		.join('|');
	return `${collection.day_count ?? ''}#${collection.start_date ?? ''}#${days}#${items}`;
}
