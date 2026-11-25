import { beforeEach, describe, expect, it } from 'vitest';
import type { CollectionItineraryDay } from '#lib/types.js';
import {
	canUnlinkPlace,
	dayLink,
	initialPlanDay,
	recordedVisit,
	initialTravelers,
	rememberedTravelers,
	rememberTravelers,
	tripToday
} from './plan';

function day(index: number, date: string | null): CollectionItineraryDay {
	return { id: `d${index}`, index, date } as unknown as CollectionItineraryDay;
}

const days = [day(1, '2026-10-28'), day(2, '2026-10-29'), day(3, '2026-10-30')];
const params = (query: string) => new URLSearchParams(query);

describe('initialPlanDay (#1346)', () => {
	it('opens the day named by ?day=', () => {
		expect(initialPlanDay(days, params('day=3'), '2026-01-01')).toBe(3);
	});

	it('opens the day with the date named by ?date=', () => {
		expect(initialPlanDay(days, params('date=2026-10-29'), '2026-01-01')).toBe(2);
	});

	it('prefers ?day= over ?date=', () => {
		expect(initialPlanDay(days, params('day=1&date=2026-10-30'), '2026-01-01')).toBe(1);
	});

	it('opens today during the trip when the link names no day', () => {
		expect(initialPlanDay(days, params(''), '2026-10-30')).toBe(3);
	});

	it('falls back to today when the named day does not exist', () => {
		expect(initialPlanDay(days, params('day=9'), '2026-10-29')).toBe(2);
		expect(initialPlanDay(days, params('date=2027-01-01'), '2026-10-29')).toBe(2);
		expect(initialPlanDay(days, params('day=abc'), '2026-10-29')).toBe(2);
	});

	it('stays at the top before or after the trip', () => {
		expect(initialPlanDay(days, params(''), '2026-11-15')).toBeNull();
	});

	it('works for trips planned by day number without dates', () => {
		const undated = [day(1, null), day(2, null)];
		expect(initialPlanDay(undated, params('day=2'), '2026-10-29')).toBe(2);
		expect(initialPlanDay(undated, params(''), '2026-10-29')).toBeNull();
	});
});

describe('dayLink', () => {
	const base = 'https://al.example/collections/abc';

	it('links to the day in the itinerary', () => {
		expect(dayLink(new URL(`${base}?view=plan`), 3)).toBe(`${base}?view=itinerary&day=3`);
	});

	it('keeps the read view and an unlisted story secret, and drops ?date=', () => {
		expect(dayLink(new URL(`${base}?view=read&s=xyz&date=2026-10-29`), 2)).toBe(
			`${base}?view=read&s=xyz&day=2`
		);
	});

	it('drops parameters a reader does not need', () => {
		expect(dayLink(new URL(`${base}?view=map&guest=tok#x`), 1)).toBe(
			`${base}?view=itinerary&day=1`
		);
	});
});

describe('tripToday', () => {
	// 03:30 UTC on 30 Oct is still 29 Oct in New York and already 30 Oct in Tokyo.
	const now = new Date('2026-10-30T03:30:00Z');

	it("uses the trip's time zone", () => {
		expect(tripToday('America/New_York', now)).toBe('2026-10-29');
		expect(tripToday('Asia/Tokyo', now)).toBe('2026-10-30');
	});

	it("uses the device's own date when the trip has no time zone", () => {
		const local = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
		expect(tripToday('UTC', now)).toBe(local);
		expect(tripToday(null, now)).toBe(local);
	});
});

describe('remembered travelers', () => {
	const store = new Map<string, string>();
	beforeEach(() => {
		store.clear();
		(globalThis as any).localStorage = {
			getItem: (key: string) => store.get(key) ?? null,
			setItem: (key: string, value: string) => void store.set(key, value),
			removeItem: (key: string) => void store.delete(key)
		};
	});

	it('round-trips the picks for a trip, per person', () => {
		rememberTravelers('c1', 'me', ['a']);
		expect(rememberedTravelers('c1', 'me')).toEqual(['a']);
		expect(store.has('trip-travelers:v3:me:c1')).toBe(true);
		// Another account on the same browser starts fresh.
		expect(rememberedTravelers('c1', 'you')).toEqual([]);
	});

	it('remembers nothing without a signed-in user', () => {
		rememberTravelers('c1', null, ['a']);
		expect(store.size).toBe(0);
		expect(rememberedTravelers('c1', null)).toEqual([]);
	});

	it('is empty for a trip with no picks', () => {
		expect(rememberedTravelers('missing', 'me')).toEqual([]);
	});

	it('is empty when the stored value is not a list of uuids', () => {
		store.set('trip-travelers:v3:me:c1', '{not json');
		expect(rememberedTravelers('c1', 'me')).toEqual([]);
		store.set('trip-travelers:v3:me:c1', '{"a":1}');
		expect(rememberedTravelers('c1', 'me')).toEqual([]);
	});

	it('starts from the current user when nothing is remembered', () => {
		expect(initialTravelers('c1', ['me', 'sam'], 'me')).toEqual(['me']);
		expect(initialTravelers('c1', ['sam'], null)).toEqual([]);
	});

	it('starts from picks that leave the current user off, dropping people who left', () => {
		rememberTravelers('c1', 'me', ['sam', 'gone']);
		expect(initialTravelers('c1', ['me', 'sam'], 'me')).toEqual(['sam']);
		rememberTravelers('c1', 'me', ['gone']);
		expect(initialTravelers('c1', ['me', 'sam'], 'me')).toEqual(['me']);
	});

	it('is empty without storage', () => {
		delete (globalThis as any).localStorage;
		expect(rememberedTravelers('c1', 'me')).toEqual([]);
		expect(() => rememberTravelers('c1', 'me', ['a'])).not.toThrow();
	});
});

describe('recordedVisit', () => {
	const collection = {
		locations: [{ id: 'L1', visits: [{ id: 'v1', start_date: '2026-10-28', travelers: [] }] }]
	} as any;

	it('finds the visit object behind a logged stop', () => {
		const item = { object_id: 'L1', logged_visit: 'v1' } as any;
		expect(recordedVisit(collection, item)?.id).toBe('v1');
	});

	it('is null when the stop is not logged', () => {
		expect(recordedVisit(collection, { object_id: 'L1' } as any)).toBeNull();
	});
});

describe('canUnlinkPlace', () => {
	const collection = { user: 'owner-uuid' };
	const row = (uuid: string) => ({ object: { user: { uuid } } }) as never;

	it("lets the collection owner unlink anyone's place", () => {
		expect(canUnlinkPlace(collection, row('someone-else'), 'owner-uuid')).toBe(true);
	});

	it("lets the place owner unlink their own place from another person's collection", () => {
		expect(canUnlinkPlace(collection, row('editor-uuid'), 'editor-uuid')).toBe(true);
	});

	it('refuses an editor who owns neither', () => {
		expect(canUnlinkPlace(collection, row('someone-else'), 'editor-uuid')).toBe(false);
		expect(canUnlinkPlace(collection, row('someone-else'), null)).toBe(false);
	});

	it('works on a location card (the object is the location itself)', () => {
		const card = { object: { user: { uuid: 'someone-else' } } } as never;
		expect(canUnlinkPlace(collection, card, 'editor-uuid')).toBe(false);
		expect(canUnlinkPlace(collection, card, 'owner-uuid')).toBe(true);
		expect(canUnlinkPlace(collection, card, 'someone-else')).toBe(true);
	});
});
