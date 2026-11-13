import { describe, expect, it } from 'vitest';
import type { Collection, CollectionItineraryItem } from '#lib/types.js';
import { buildCollectionCalendarEvents } from './events';

const labels = { eventTimezone: 'Event', localTimezone: 'Local' };
const t = (key: string) => key;

function placement(
	id: string,
	type: string,
	objectId: string,
	date: string | null,
	extra: Partial<CollectionItineraryItem> = {}
): CollectionItineraryItem {
	return {
		id,
		collection: 'c1',
		content_type: type,
		object_id: objectId,
		date,
		day_index: date ? Number(date.slice(-2)) - 9 : null,
		order: 0,
		created_at: '2026-01-01T00:00:00Z',
		start_datetime: null,
		end_datetime: null,
		...extra
	} as CollectionItineraryItem;
}

function trip(
	itinerary: CollectionItineraryItem[],
	overrides: Partial<Collection> = {}
): Collection {
	return {
		id: 'c1',
		name: 'Japan',
		timezone: 'Asia/Tokyo',
		start_date: '2026-11-10',
		end_date: '2026-11-14',
		locations: [
			{
				id: 'loc-temple',
				name: 'Kinkaku-ji',
				location: 'Kyoto',
				category: { icon: '⛩️', display_name: 'Temple' },
				visits: []
			},
			{
				id: 'loc-tower',
				name: 'Tokyo Tower',
				category: null,
				visits: [{ id: 'v1', start_date: '2026-11-12', end_date: '2026-11-12' }]
			}
		],
		notes: [{ id: 'note-1', name: 'Pack the JR pass', content: 'In the blue folder' }],
		checklists: [{ id: 'list-1', name: 'Onsen kit' }],
		lodging: [{ id: 'stay-1', name: 'Ryokan', check_in: null, check_out: null }],
		transportations: [],
		itinerary,
		itinerary_days: [],
		...overrides
	} as unknown as Collection;
}

const build = (collection: Collection) =>
	buildCollectionCalendarEvents(collection, 'event', 'UTC', labels, t);

describe('buildCollectionCalendarEvents: itinerary (#1260)', () => {
	it('shows a place planned only in the itinerary as an all-day stop', () => {
		const events = build(trip([placement('p1', 'location', 'loc-temple', '2026-11-11')]));
		const stop = events.find((event) => event.id === 'stop-p1');
		expect(stop).toBeDefined();
		expect(stop!.title).toBe('⛩️ Kinkaku-ji');
		expect(stop!.start).toBe('2026-11-11');
		expect(stop!.end).toBe('2026-11-12');
		expect(stop!.extendedProps.type).toBe('stop');
		expect(stop!.extendedProps.isAllDay).toBe(true);
		expect(stop!.extendedProps.url).toBe('/locations/loc-temple');
	});

	it('follows the placement when it moves to another day', () => {
		const moved = build(trip([placement('p1', 'location', 'loc-temple', '2026-11-13')]));
		expect(moved.find((event) => event.id === 'stop-p1')!.start).toBe('2026-11-13');
	});

	it('covers every day of a spanning placement', () => {
		const events = build(
			trip([placement('p1', 'location', 'loc-temple', '2026-11-11', { span_end_index: 4 })])
		);
		const stop = events.find((event) => event.id === 'stop-p1')!;
		expect(stop.start).toBe('2026-11-11');
		expect(stop.end).toBe('2026-11-14');
	});

	it('uses the planned time when the stop has one', () => {
		const events = build(
			trip([
				placement('p1', 'location', 'loc-temple', '2026-11-11', {
					start_time: '09:00:00',
					end_time: '11:30:00',
					timezone: 'Asia/Tokyo',
					start_datetime: '2026-11-11T09:00:00+09:00',
					end_datetime: '2026-11-11T11:30:00+09:00'
				})
			])
		);
		const stop = events.find((event) => event.id === 'stop-p1')!;
		expect(stop.extendedProps.isAllDay).toBe(false);
		expect(stop.start).toBe('2026-11-11T09:00:00.000+09:00');
		expect(stop.end).toBe('2026-11-11T11:30:00.000+09:00');
	});

	it('does not repeat a stop that already has a visit on that day', () => {
		const events = build(trip([placement('p2', 'location', 'loc-tower', '2026-11-12')]));
		expect(events.some((event) => event.id === 'stop-p2')).toBe(false);
		expect(events.filter((event) => event.id.startsWith('location-loc-tower'))).toHaveLength(1);
	});

	it('shows dated notes and checklists', () => {
		const events = build(
			trip([
				placement('p3', 'note', 'note-1', '2026-11-10'),
				placement('p4', 'checklist', 'list-1', '2026-11-14')
			])
		);
		const note = events.find((event) => event.id === 'note-p3')!;
		expect(note.title).toBe('📝 Pack the JR pass');
		expect(note.extendedProps.description).toBe('In the blue folder');
		expect(events.find((event) => event.id === 'checklist-p4')!.start).toBe('2026-11-14');
	});

	it('places a stay without its own dates on its itinerary days', () => {
		const events = build(
			trip([placement('p5', 'lodging', 'stay-1', '2026-11-11', { span_end_index: 3 })])
		);
		const stay = events.find((event) => event.id === 'lodging-stay-1')!;
		expect(stay.start).toBe('2026-11-11');
		expect(stay.end).toBe('2026-11-13');
	});

	it('leaves a stay with its own dates where those dates put it', () => {
		const collection = trip([placement('p5', 'lodging', 'stay-1', '2026-11-13')]);
		(collection.lodging![0] as any).check_in = '2026-11-10';
		(collection.lodging![0] as any).check_out = '2026-11-12';
		const stays = build(collection).filter((event) => event.id === 'lodging-stay-1');
		expect(stays).toHaveLength(1);
		expect(stays[0].start).toBe('2026-11-10');
	});

	it('skips trip-wide, optional and undated placements', () => {
		const events = build(
			trip([
				placement('g', 'note', 'note-1', null, { is_global: true }),
				placement('o', 'location', 'loc-temple', '2026-11-11', { is_optional: true }),
				placement('u', 'location', 'loc-temple', null)
			])
		);
		expect(events.some((event) => /^(stop|note)-/.test(event.id))).toBe(false);
	});
});
