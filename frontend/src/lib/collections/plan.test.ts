import { describe, expect, it } from 'vitest';
import type { CollectionItineraryDay } from '#lib/types.js';
import { dayLink, initialPlanDay, tripToday } from './plan';

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
