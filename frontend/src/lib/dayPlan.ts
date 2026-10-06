import type {
	Checklist,
	Collection,
	CollectionItineraryDay,
	CollectionItineraryItem,
	Location,
	Lodging,
	Note,
	Transportation
} from '$lib/types';

export const MAX_PLAN_DAYS = 62;
export const DEFAULT_PLAN_DAYS = 21;

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

export function isDayBased(collection: Collection): boolean {
	return collection.type === 'trip' && Boolean(collection.day_count);
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

export function errorMessage(data: any, fallback: string): string {
	if (!data) return fallback;
	if (typeof data.error === 'string') return data.error;
	if (typeof data.detail === 'string') return data.detail;
	for (const value of Object.values(data)) {
		if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
		if (typeof value === 'string') return value;
	}
	return fallback;
}

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
