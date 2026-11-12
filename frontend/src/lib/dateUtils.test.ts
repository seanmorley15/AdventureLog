import { describe, expect, it } from 'vitest';
import {
	defaultTimezone,
	getEntitiesInDateRange,
	getEntitiesOutsideDateRange,
	inclusiveDayCount,
	isEntityInCollectionDateRange,
	nightsBetween,
	toDateOnlyLocal,
	toLocalDatetime,
	toTimedLocalDefault,
	toUTCDatetime,
	validateDateRange
} from './dateUtils';
import type { Collection } from './types';

// These tests run with TZ=UTC (see vite.config.ts) so results do not depend on the machine.
// Everything that matters across zones passes an explicit IANA zone.

const asCollection = (start: string | null, end: string | null) =>
	({ start_date: start, end_date: end }) as unknown as Collection;
// The helpers accept several entity shapes; tests build the minimal fields they read.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const entity = (fields: Record<string, unknown>) => fields as any;

describe('toLocalDatetime', () => {
	it('converts a UTC instant to a datetime-local value in the zone', () => {
		expect(toLocalDatetime('2027-06-01T12:00:00Z', 'America/New_York')).toBe('2027-06-01T08:00');
		expect(toLocalDatetime('2027-06-01T12:00:00Z', 'Asia/Tokyo')).toBe('2027-06-01T21:00');
	});

	it('crosses the date line correctly', () => {
		expect(toLocalDatetime('2027-06-01T23:30:00Z', 'Pacific/Auckland')).toBe('2027-06-02T11:30');
	});

	it('returns an empty string for empty or invalid input', () => {
		expect(toLocalDatetime(null, 'UTC')).toBe('');
		expect(toLocalDatetime('not a date', 'UTC')).toBe('');
	});
});

describe('toUTCDatetime', () => {
	it('converts a zoned local time to UTC', () => {
		expect(toUTCDatetime('2027-06-01T08:00', 'America/New_York')).toBe('2027-06-01T12:00:00Z');
		expect(toUTCDatetime('2027-06-01T21:00', 'Asia/Tokyo')).toBe('2027-06-01T12:00:00Z');
	});

	it('respects daylight saving time', () => {
		expect(toUTCDatetime('2027-01-15T08:00', 'America/New_York')).toBe('2027-01-15T13:00:00Z');
		expect(toUTCDatetime('2027-07-15T08:00', 'America/New_York')).toBe('2027-07-15T12:00:00Z');
	});

	it('pins all-day values to UTC midnight regardless of zone', () => {
		expect(toUTCDatetime('2027-06-01', 'Asia/Tokyo', true)).toBe('2027-06-01T00:00:00Z');
		expect(toUTCDatetime('2027-06-01T15:00', 'America/Los_Angeles', true)).toBe(
			'2027-06-01T00:00:00Z'
		);
	});

	it('returns null for an empty value', () => {
		expect(toUTCDatetime('', 'UTC')).toBeNull();
	});

	it('round-trips with toLocalDatetime', () => {
		for (const zone of ['America/New_York', 'Europe/Paris', 'Asia/Kolkata', 'Pacific/Auckland']) {
			const utc = toUTCDatetime('2027-03-14T09:45', zone)!;
			expect(toLocalDatetime(utc, zone)).toBe('2027-03-14T09:45');
		}
	});
});

describe('all-day input helpers', () => {
	it('strips the time portion', () => {
		expect(toDateOnlyLocal('2027-06-01T13:30')).toBe('2027-06-01');
		expect(toDateOnlyLocal('')).toBe('');
	});

	it('adds start and end of day defaults when switching to timed', () => {
		expect(toTimedLocalDefault('2027-06-01')).toBe('2027-06-01T00:00');
		expect(toTimedLocalDefault('2027-06-01', true)).toBe('2027-06-01T23:59');
		expect(toTimedLocalDefault('')).toBe('');
	});
});

describe('validateDateRange', () => {
	it('accepts empty, start-only and ordered ranges', () => {
		expect(validateDateRange('', '').valid).toBe(true);
		expect(validateDateRange('2027-06-01T10:00:00Z', '').valid).toBe(true);
		expect(validateDateRange('2027-06-01T10:00:00Z', '2027-06-01T10:00:00Z').valid).toBe(true);
		expect(validateDateRange('2027-06-01T10:00:00Z', '2027-06-02T10:00:00Z').valid).toBe(true);
	});

	it('rejects an end date without a start date', () => {
		expect(validateDateRange('', '2027-06-02T10:00:00Z').valid).toBe(false);
	});

	it('rejects an end before the start', () => {
		const result = validateDateRange('2027-06-02T10:00:00Z', '2027-06-01T10:00:00Z');
		expect(result.valid).toBe(false);
		expect(result.error).toBeTruthy();
	});
});

describe('inclusiveDayCount', () => {
	it('counts both end days', () => {
		expect(inclusiveDayCount('2027-06-01', '2027-06-01')).toBe(1);
		expect(inclusiveDayCount('2027-06-01', '2027-06-04')).toBe(4);
	});

	it('ignores time portions and spans month and year boundaries', () => {
		expect(inclusiveDayCount('2027-06-01T22:00:00Z', '2027-06-02T01:00:00Z')).toBe(2);
		expect(inclusiveDayCount('2027-12-30', '2028-01-02')).toBe(4);
		expect(inclusiveDayCount('2028-02-28', '2028-03-01')).toBe(3); // 2028 is a leap year
	});

	it('is at least 1 and null for missing or invalid input', () => {
		expect(inclusiveDayCount('2027-06-04', '2027-06-01')).toBe(1);
		expect(inclusiveDayCount(null, '2027-06-01')).toBeNull();
		expect(inclusiveDayCount('2027-06-01', undefined)).toBeNull();
		expect(inclusiveDayCount('garbage', '2027-06-01')).toBeNull();
	});
});

describe('nightsBetween', () => {
	it('counts nights between all-day dates', () => {
		expect(nightsBetween('2027-06-01', '2027-06-04')).toBe(3);
		expect(nightsBetween('2027-06-01T00:00:00Z', '2027-06-02T00:00:00Z')).toBe(1);
	});

	it('uses calendar days in the entry zone, so a late check-in does not shift', () => {
		// 23:00 in New York on 1 June is 03:00 UTC on 2 June.
		expect(nightsBetween('2027-06-02T03:00:00Z', '2027-06-04T15:00:00Z', 'America/New_York')).toBe(
			3
		);
	});

	it('is null for zero or negative stays and missing input', () => {
		expect(nightsBetween('2027-06-01', '2027-06-01')).toBeNull();
		expect(nightsBetween('2027-06-05', '2027-06-01')).toBeNull();
		expect(nightsBetween(null, '2027-06-01')).toBeNull();
		expect(nightsBetween('2027-06-01', undefined)).toBeNull();
	});
});

describe('isEntityInCollectionDateRange', () => {
	const trip = asCollection('2027-06-10', '2027-06-14');

	it('is false when the collection has no dates', () => {
		const visit = entity({ start_date: '2027-06-11T00:00:00Z', end_date: '2027-06-11T00:00:00Z' });
		expect(isEntityInCollectionDateRange(visit, asCollection(null, null))).toBe(false);
		expect(isEntityInCollectionDateRange(visit, asCollection('2027-06-10', null))).toBe(false);
	});

	describe('all-day visits', () => {
		const visit = (start: string, end: string) =>
			entity({ start_date: `${start}T00:00:00Z`, end_date: `${end}T00:00:00Z` });

		it('includes visits inside, on the edges of, and overlapping the trip', () => {
			expect(isEntityInCollectionDateRange(visit('2027-06-11', '2027-06-12'), trip)).toBe(true);
			expect(isEntityInCollectionDateRange(visit('2027-06-10', '2027-06-10'), trip)).toBe(true);
			expect(isEntityInCollectionDateRange(visit('2027-06-14', '2027-06-14'), trip)).toBe(true);
			expect(isEntityInCollectionDateRange(visit('2027-06-08', '2027-06-11'), trip)).toBe(true);
			expect(isEntityInCollectionDateRange(visit('2027-06-01', '2027-06-30'), trip)).toBe(true);
		});

		it('excludes visits entirely before or after', () => {
			expect(isEntityInCollectionDateRange(visit('2027-06-01', '2027-06-09'), trip)).toBe(false);
			expect(isEntityInCollectionDateRange(visit('2027-06-15', '2027-06-20'), trip)).toBe(false);
		});
	});

	describe('timed visits', () => {
		const timedTrip = asCollection('2027-06-10T00:00:00Z', '2027-06-14T23:59:59Z');

		it('includes visits whose time falls inside the trip', () => {
			const inside = entity({
				start_date: '2027-06-11T09:00:00Z',
				end_date: '2027-06-11T17:00:00Z',
				timezone: 'UTC'
			});
			expect(isEntityInCollectionDateRange(inside, timedTrip)).toBe(true);
		});

		it('excludes visits that end before the trip starts', () => {
			const before = entity({
				start_date: '2027-06-09T09:00:00Z',
				end_date: '2027-06-09T17:00:00Z',
				timezone: 'UTC'
			});
			expect(isEntityInCollectionDateRange(before, timedTrip)).toBe(false);
		});
	});

	it('handles transportation (date + end_date)', () => {
		const train = entity({ date: '2027-06-12', end_date: '2027-06-12' });
		expect(isEntityInCollectionDateRange(train, trip)).toBe(true);
		const late = entity({ date: '2027-06-20', end_date: '2027-06-20' });
		expect(isEntityInCollectionDateRange(late, trip)).toBe(false);
	});

	it('handles lodging (check_in + check_out)', () => {
		const hotel = entity({ check_in: '2027-06-09', check_out: '2027-06-11' });
		expect(isEntityInCollectionDateRange(hotel, trip)).toBe(true);
		const elsewhere = entity({ check_in: '2027-07-01', check_out: '2027-07-03' });
		expect(isEntityInCollectionDateRange(elsewhere, trip)).toBe(false);
	});

	it('handles single-date entities such as notes and checklists', () => {
		expect(isEntityInCollectionDateRange(entity({ date: '2027-06-12' }), trip)).toBe(true);
		expect(isEntityInCollectionDateRange(entity({ date: '2027-05-01' }), trip)).toBe(false);
	});

	it('does not match entities with no dates at all', () => {
		expect(isEntityInCollectionDateRange(entity({ name: 'undated' }), trip)).toBe(false);
	});
});

describe('getEntitiesInDateRange / getEntitiesOutsideDateRange', () => {
	const trip = asCollection('2027-06-10', '2027-06-14');
	const inside = entity({ id: 'in', date: '2027-06-12' });
	const outside = entity({ id: 'out', date: '2027-09-01' });

	it('partition entities', () => {
		const all = [inside, outside];
		expect(getEntitiesInDateRange(all, trip)).toEqual([inside]);
		expect(getEntitiesOutsideDateRange(all, trip)).toEqual([outside]);
	});
});

// #653, #801: new times entered inside a trip start in the trip's zone.
describe('defaultTimezone', () => {
	const browser = Intl.DateTimeFormat().resolvedOptions().timeZone;

	it("uses the trip's time zone", () => {
		expect(defaultTimezone({ timezone: 'Asia/Tokyo' })).toBe('Asia/Tokyo');
	});

	it("uses this browser's zone outside a collection or when the trip has none", () => {
		expect(defaultTimezone(null)).toBe(browser);
		expect(defaultTimezone(undefined)).toBe(browser);
		expect(defaultTimezone({ timezone: null })).toBe(browser);
		// Collections store 'UTC' until a zone is chosen.
		expect(defaultTimezone({ timezone: 'UTC' })).toBe(browser);
	});
});
