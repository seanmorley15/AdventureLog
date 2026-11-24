/**
 * The published story as chapters.
 *
 * Works from the story payload (`?as=story`, or what a public reader receives),
 * which only carries the groups the owner turned on. A missing field is simply
 * not shown; nothing here asks for more data.
 */
import type {
	Activity,
	Checklist,
	Collection,
	CollectionItineraryDay,
	CollectionItineraryItem,
	ContentImage,
	DayImage,
	Location,
	Lodging,
	Note,
	StoryGroup,
	Trail,
	Transportation
} from '#lib/types.js';
import { dayPinColor, findObject, indexedDays, placementType } from '#lib/collections/plan.js';

export const STORY_GROUP_NAMES: StoryGroup[] = [
	'place_details',
	'costs',
	'reservations',
	'attachments',
	'lodging_address',
	'coordinates',
	'gpx',
	'note_text',
	'checklist_text'
];

export type StoryEntry =
	| { kind: 'location'; key: string; object: Location; item: CollectionItineraryItem | null }
	| {
			kind: 'lodging';
			key: string;
			object: Lodging;
			item: CollectionItineraryItem | null;
			continued: boolean;
	  }
	| {
			kind: 'transportation';
			key: string;
			object: Transportation;
			item: CollectionItineraryItem | null;
	  }
	| { kind: 'note'; key: string; object: Note; item: CollectionItineraryItem | null }
	| { kind: 'checklist'; key: string; object: Checklist; item: CollectionItineraryItem | null }
	| { kind: 'activity'; key: string; object: Activity; item: null }
	| { kind: 'trail'; key: string; object: Trail; item: null };

export type StoryPin = {
	key: string; // entry key the pin belongs to
	chapter: string;
	label: string;
	name: string;
	lat: number;
	lng: number;
	color: string;
	kind: 'location' | 'lodging' | 'transportation';
};

export type StoryChapter = {
	key: string;
	index: number | null; // Day number, null for trip-wide or a places list
	date: string | null;
	name: string | null;
	description: string | null;
	entries: StoryEntry[];
	photos: ContentImage[];
	pins: StoryPin[];
	tracks: Activity[];
	color: string;
};

export type Story = {
	chapters: StoryChapter[];
	pins: StoryPin[];
	tracks: Activity[];
	photos: ContentImage[];
	placeCount: number;
	dayCount: number;
	distanceMeters: number;
};

function isNumber(value: unknown): value is number {
	return typeof value === 'number' && Number.isFinite(value);
}

function entryKey(kind: string, id: string, suffix = '') {
	return `${kind}-${id}${suffix}`;
}

function entryFor(
	collection: Collection,
	item: CollectionItineraryItem,
	continued = false
): StoryEntry | null {
	const type = placementType(item);
	const object = findObject(collection, type, String(item.object_id));
	if (!type || !object) return null;
	const key = entryKey(type, String(object.id), continued ? `-${item.id}-cont` : `-${item.id}`);
	switch (type) {
		case 'location':
			return { kind: 'location', key, object: object as Location, item };
		case 'lodging':
			return { kind: 'lodging', key, object: object as Lodging, item, continued };
		case 'transportation':
			return { kind: 'transportation', key, object: object as Transportation, item };
		case 'note':
			return { kind: 'note', key, object: object as Note, item };
		case 'checklist':
			return { kind: 'checklist', key, object: object as Checklist, item };
	}
	return null;
}

function pinsFor(entries: StoryEntry[], chapterKey: string, color: string): StoryPin[] {
	const pins: StoryPin[] = [];
	let number = 0;
	for (const entry of entries) {
		if (entry.kind === 'location') {
			const { latitude, longitude, name } = entry.object;
			if (isNumber(latitude) && isNumber(longitude)) {
				number += 1;
				pins.push({
					key: entry.key,
					chapter: chapterKey,
					label: String(number),
					name,
					lat: latitude,
					lng: longitude,
					color,
					kind: 'location'
				});
			}
		} else if (entry.kind === 'lodging' && !entry.continued) {
			const { latitude, longitude, name } = entry.object;
			if (isNumber(latitude) && isNumber(longitude)) {
				pins.push({
					key: entry.key,
					chapter: chapterKey,
					label: '🛏',
					name,
					lat: latitude,
					lng: longitude,
					color,
					kind: 'lodging'
				});
			}
		} else if (entry.kind === 'transportation') {
			const t = entry.object;
			if (isNumber(t.destination_latitude) && isNumber(t.destination_longitude)) {
				pins.push({
					key: entry.key,
					chapter: chapterKey,
					label: '✈',
					name: t.to_location || t.name,
					lat: t.destination_latitude,
					lng: t.destination_longitude,
					color,
					kind: 'transportation'
				});
			}
		}
	}
	return pins;
}

function dayImages(collection: Collection, day: CollectionItineraryDay): ContentImage[] {
	const activityIds = new Set(
		(collection.day_activities ?? []).filter((a) => a.day === day.id).map((a) => String(a.id))
	);
	const trailIds = new Set(
		(collection.day_trails ?? []).filter((t) => t.day === day.id).map((t) => String(t.id))
	);
	return (collection.day_images ?? []).filter((image: DayImage) => {
		const id = String(image.object_id);
		if (image.content_type === 'collectionitineraryday') return id === String(day.id);
		if (image.content_type === 'activity') return activityIds.has(id);
		if (image.content_type === 'trail') return trailIds.has(id);
		return false;
	});
}

function sortItems(items: CollectionItineraryItem[]) {
	return [...items].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
}

function finishChapter(chapter: Omit<StoryChapter, 'pins'>): StoryChapter {
	return { ...chapter, pins: pinsFor(chapter.entries, chapter.key, chapter.color) };
}

/** Day-based trips: one chapter per day, plus trip-wide notes first. */
function dayChapters(collection: Collection): StoryChapter[] {
	const days = indexedDays(collection);
	// Ideas are planning only. Optional stops on a day stay, marked optional.
	const items = (collection.itinerary ?? []).filter((item) => item.day || item.is_global);
	const chapters: StoryChapter[] = [];

	const global = sortItems(items.filter((item) => item.is_global))
		.map((item) => entryFor(collection, item))
		.filter((entry): entry is StoryEntry => entry !== null);
	if (global.length) {
		chapters.push(
			finishChapter({
				key: 'trip',
				index: null,
				date: null,
				name: null,
				description: null,
				entries: global,
				photos: [],
				tracks: [],
				color: '#64748b'
			})
		);
	}

	for (const day of days) {
		const index = day.index ?? 0;
		const color = dayPinColor(index);
		const entries: StoryEntry[] = [];
		// A stay that started on an earlier day is listed as continuing.
		for (const item of items) {
			if (!item.day || item.day === day.id || placementType(item) !== 'lodging') continue;
			const start = item.day_index ?? 0;
			const end = item.span_end_index ?? start;
			if (start < index && index <= end) {
				const entry = entryFor(collection, item, true);
				if (entry) entries.push(entry);
			}
		}
		for (const item of sortItems(items.filter((item) => item.day === day.id))) {
			const entry = entryFor(collection, item);
			if (entry) entries.push(entry);
		}
		const activities = (collection.day_activities ?? []).filter((a) => a.day === day.id);
		for (const activity of activities) {
			entries.push({
				kind: 'activity',
				key: entryKey('activity', activity.id),
				object: activity,
				item: null
			});
		}
		for (const trail of collection.day_trails ?? []) {
			if (!trail.day) continue;
			const start = trail.day_index ?? 0;
			const end = trail.span_end_index ?? start;
			if (trail.day === day.id || (start < index && index <= end)) {
				entries.push({
					kind: 'trail',
					key: entryKey('trail', trail.id, `-${day.id}`),
					object: trail,
					item: null
				});
			}
		}
		chapters.push(
			finishChapter({
				key: `day-${day.id}`,
				index,
				date: day.date,
				name: day.name,
				description: day.description,
				entries,
				photos: dayImages(collection, day),
				tracks: activities.filter((a) => a.geojson),
				color
			})
		);
	}
	return chapters;
}

/** Date-keyed trips: one chapter per itinerary date. */
function dateChapters(collection: Collection): StoryChapter[] {
	const byDate = new Map<string, CollectionItineraryItem[]>();
	for (const item of collection.itinerary ?? []) {
		if (!item.date || item.is_global) continue;
		byDate.set(item.date, [...(byDate.get(item.date) ?? []), item]);
	}
	return [...byDate.keys()].sort().map((date, i) =>
		finishChapter({
			key: `date-${date}`,
			index: i + 1,
			date,
			name: null,
			description: null,
			entries: sortItems(byDate.get(date) ?? [])
				.map((item) => entryFor(collection, item))
				.filter((entry): entry is StoryEntry => entry !== null),
			photos: [],
			tracks: [],
			color: dayPinColor(i + 1)
		})
	);
}

/** Folders and trips with nothing scheduled: one chapter of places. */
function placeChapter(collection: Collection): StoryChapter[] {
	const entries: StoryEntry[] = [
		...(collection.locations ?? []).map(
			(object): StoryEntry => ({
				kind: 'location',
				key: entryKey('location', object.id),
				object,
				item: null
			})
		),
		...(collection.lodging ?? []).map(
			(object): StoryEntry => ({
				kind: 'lodging',
				key: entryKey('lodging', object.id),
				object,
				item: null,
				continued: false
			})
		),
		...(collection.notes ?? []).map(
			(object): StoryEntry => ({
				kind: 'note',
				key: entryKey('note', object.id),
				object,
				item: null
			})
		)
	];
	if (!entries.length) return [];
	return [
		finishChapter({
			key: 'places',
			index: null,
			date: null,
			name: null,
			description: null,
			entries,
			photos: [],
			tracks: [],
			color: dayPinColor(1)
		})
	];
}

export function buildStory(collection: Collection): Story {
	let chapters = indexedDays(collection).length
		? dayChapters(collection)
		: dateChapters(collection);
	if (!chapters.some((chapter) => chapter.entries.length || chapter.photos.length)) {
		chapters = placeChapter(collection);
	}

	const photos: ContentImage[] = [];
	const seen = new Set<string>();
	const addPhoto = (image: ContentImage | null | undefined) => {
		if (image?.image && !seen.has(image.image)) {
			seen.add(image.image);
			photos.push(image);
		}
	};
	addPhoto(collection.primary_image);
	for (const chapter of chapters) {
		for (const entry of chapter.entries) {
			if (entry.kind === 'location' || entry.kind === 'lodging') {
				for (const image of entry.object.images ?? []) addPhoto(image);
			}
		}
		chapter.photos.forEach(addPhoto);
	}

	const placeIds = new Set(
		chapters.flatMap((c) =>
			c.entries.filter((e) => e.kind === 'location').map((e) => String(e.object.id))
		)
	);
	const tracks = chapters.flatMap((chapter) => chapter.tracks);
	return {
		chapters,
		pins: chapters.flatMap((chapter) => chapter.pins),
		tracks,
		photos,
		placeCount: placeIds.size,
		dayCount: chapters.filter((chapter) => chapter.index !== null).length,
		distanceMeters: (collection.day_activities ?? []).reduce(
			(sum, activity) => sum + (activity.distance ?? 0),
			0
		)
	};
}

/** Story groups the owner has left off, for the preview bar. */
export function hiddenStoryGroups(collection: Collection): StoryGroup[] {
	return STORY_GROUP_NAMES.filter((group) => !collection.story_groups?.[group]);
}

/** Bounds for a set of pins, padded so a single pin still zooms sensibly. */
export function pinBounds(
	pins: Pick<StoryPin, 'lat' | 'lng'>[]
): [[number, number], [number, number]] | null {
	if (!pins.length) return null;
	let minLng = Infinity;
	let minLat = Infinity;
	let maxLng = -Infinity;
	let maxLat = -Infinity;
	for (const pin of pins) {
		minLng = Math.min(minLng, pin.lng);
		maxLng = Math.max(maxLng, pin.lng);
		minLat = Math.min(minLat, pin.lat);
		maxLat = Math.max(maxLat, pin.lat);
	}
	const pad = 0.01;
	return [
		[minLng - pad, minLat - pad],
		[maxLng + pad, maxLat + pad]
	];
}

export type ReadingSection = {
	/** Chapter key, or null for the cover, intro, and footer. */
	key: string | null;
	top: number;
	entries: { key: string; top: number }[];
};

/**
 * Where the reader is, from one reading line.
 *
 * The chapter is the last section whose top has passed the line. The stop is the last
 * pinned entry of that chapter that has passed the line, or the chapter's first pinned
 * entry when only its heading has, so entering a day centers on its first place.
 */
export function readingPosition(
	sections: ReadingSection[],
	line: number,
	pinned: Set<string>
): { chapter: string | null; entry: string | null } {
	let section: ReadingSection | null = null;
	for (const candidate of sections) {
		if (candidate.top > line) break;
		section = candidate;
	}
	if (!section?.key) return { chapter: null, entry: null };
	let entry: string | null = null;
	for (const candidate of section.entries) {
		if (!pinned.has(candidate.key)) continue;
		if (entry !== null && candidate.top > line) break;
		entry = candidate.key;
	}
	return { chapter: section.key, entry };
}
