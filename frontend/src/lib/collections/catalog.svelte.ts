import type { Checklist, Collection, Location, Lodging, Note, Transportation } from '$lib/types';

export type CatalogSort = 'name-asc' | 'name-desc' | 'date-asc' | 'date-desc' | 'visited';

export class CatalogFilters {
	search = $state('');
	showLocations = $state(true);
	showLodging = $state(true);
	showTransportation = $state(true);
	showNotes = $state(true);
	showChecklists = $state(true);
	showVisited = $state(true);
	showPlanned = $state(true);
	startDate = $state('');
	endDate = $state('');
	categories = $state(new Set<string>());
	lodgingTypes = $state(new Set<string>());
	transportTypes = $state(new Set<string>());
	showLines = $state(true);
	showTrails = $state(true);
	showImagePins = $state(true);
	numberedPins = $state(false);
	sort = $state<CatalogSort>('name-asc');

	isPristine(): boolean {
		return (
			!this.search.trim() &&
			this.showLocations &&
			this.showLodging &&
			this.showTransportation &&
			this.showNotes &&
			this.showChecklists &&
			this.showVisited &&
			this.showPlanned &&
			this.showLines &&
			this.showTrails &&
			this.showImagePins &&
			!this.numberedPins &&
			!this.startDate &&
			!this.endDate &&
			this.categories.size === 0 &&
			this.lodgingTypes.size === 0 &&
			this.transportTypes.size === 0 &&
			this.sort === 'name-asc'
		);
	}

	reset() {
		this.search = '';
		this.showLocations = true;
		this.showLodging = true;
		this.showTransportation = true;
		this.showNotes = true;
		this.showChecklists = true;
		this.showVisited = true;
		this.showPlanned = true;
		this.startDate = '';
		this.endDate = '';
		this.categories = new Set();
		this.lodgingTypes = new Set();
		this.transportTypes = new Set();
		this.showLines = true;
		this.showTrails = true;
		this.showImagePins = true;
		this.numberedPins = false;
		this.sort = 'name-asc';
	}
}

export function facetChecked(selected: Set<string>, name: string): boolean {
	return selected.size === 0 || selected.has(name);
}

/** Empty means every value is included. Checking the full list clears back to empty. */
export function toggleFacet(selected: Set<string>, name: string, all: string[]): Set<string> {
	const base = selected.size === 0 ? all : [...selected];
	const next = base.includes(name) ? base.filter((item) => item !== name) : [...base, name];
	if (next.length === 0 || next.length === all.length) return new Set();
	return new Set(next);
}

export function parseCatalogDate(value: string | null | undefined): number | null {
	if (!value) return null;
	const ts = Date.parse(value);
	return Number.isFinite(ts) ? ts : null;
}

export function isWithinDateRange(
	value: string | null | undefined,
	startDate: string,
	endDate: string
): boolean {
	if (!startDate && !endDate) return true;
	const ts = parseCatalogDate(value);
	if (!ts) return false;
	const startTs = startDate ? Date.parse(startDate) : -Infinity;
	const endTs = endDate ? Date.parse(endDate) + 24 * 60 * 60 * 1000 - 1 : Infinity;
	return ts >= startTs && ts <= endTs;
}

function textMatch(value: string | null | undefined, query: string): boolean {
	return (value ?? '').toLowerCase().includes(query);
}

function locationDate(loc: Location): string | null {
	const dates = (loc.visits ?? [])
		.map((visit) => visit?.start_date || visit?.end_date)
		.filter((date): date is string => Boolean(date))
		.sort();
	return dates[0] ?? null;
}

function lodgingDate(lodging: Lodging): string | null {
	return lodging.check_in || lodging.check_out || null;
}

function transportationDate(item: Transportation): string | null {
	return item.date || item.end_date || null;
}

function compareNames(a: string, b: string): number {
	return a.localeCompare(b);
}

function compareDates(a: string | null, b: string | null): number {
	return (a ?? '').localeCompare(b ?? '');
}

export function locationMatches(loc: Location, filters: CatalogFilters): boolean {
	if (!filters.showLocations) return false;
	const visited = Boolean(loc.is_visited || (loc.visits && loc.visits.length > 0));
	if (visited && !filters.showVisited) return false;
	if (!visited && !filters.showPlanned) return false;
	if (filters.categories.size) {
		const name = loc.category?.display_name;
		if (!name || !filters.categories.has(name)) return false;
	}
	const query = filters.search.trim().toLowerCase();
	if (
		query &&
		!textMatch(loc.name, query) &&
		!textMatch(loc.location, query) &&
		!textMatch(loc.category?.display_name, query) &&
		!textMatch(loc.description, query)
	) {
		return false;
	}
	return isWithinDateRange(locationDate(loc), filters.startDate, filters.endDate);
}

export function lodgingMatches(lodging: Lodging, filters: CatalogFilters): boolean {
	if (!filters.showLodging) return false;
	if (filters.lodgingTypes.size && !filters.lodgingTypes.has(lodging.type || 'other')) {
		return false;
	}
	const query = filters.search.trim().toLowerCase();
	if (
		query &&
		!textMatch(lodging.name, query) &&
		!textMatch(lodging.location, query) &&
		!textMatch(lodging.type, query) &&
		!textMatch(lodging.description, query)
	) {
		return false;
	}
	return isWithinDateRange(lodgingDate(lodging), filters.startDate, filters.endDate);
}

export function transportationMatches(item: Transportation, filters: CatalogFilters): boolean {
	if (!filters.showTransportation) return false;
	if (filters.transportTypes.size && !filters.transportTypes.has(item.type || 'other')) {
		return false;
	}
	const query = filters.search.trim().toLowerCase();
	if (
		query &&
		!textMatch(item.name, query) &&
		!textMatch(item.type, query) &&
		!textMatch(item.from_location, query) &&
		!textMatch(item.to_location, query) &&
		!textMatch(item.description, query)
	) {
		return false;
	}
	return isWithinDateRange(transportationDate(item), filters.startDate, filters.endDate);
}

export function noteMatches(note: Note, filters: CatalogFilters): boolean {
	if (!filters.showNotes) return false;
	const query = filters.search.trim().toLowerCase();
	if (query && !textMatch(note.name, query) && !textMatch(note.content, query)) return false;
	return isWithinDateRange(note.date, filters.startDate, filters.endDate);
}

export function checklistMatches(checklist: Checklist, filters: CatalogFilters): boolean {
	if (!filters.showChecklists) return false;
	const query = filters.search.trim().toLowerCase();
	if (query && !textMatch(checklist.name, query)) return false;
	return isWithinDateRange(checklist.date, filters.startDate, filters.endDate);
}

export function sortLocations(items: Location[], sort: CatalogSort): Location[] {
	const next = [...items];
	switch (sort) {
		case 'name-desc':
			return next.sort((a, b) => compareNames(b.name, a.name));
		case 'visited':
			return next.sort((a, b) => {
				const aVisited = a.visits && a.visits.length > 0 ? 1 : 0;
				const bVisited = b.visits && b.visits.length > 0 ? 1 : 0;
				return bVisited - aVisited || compareNames(a.name, b.name);
			});
		case 'date-asc':
			return next.sort((a, b) => compareDates(locationDate(a), locationDate(b)));
		case 'date-desc':
			return next.sort((a, b) => compareDates(locationDate(b), locationDate(a)));
		default:
			return next.sort((a, b) => compareNames(a.name, b.name));
	}
}

export function sortByNameAndDate<T extends { name: string; date?: string | null }>(
	items: T[],
	sort: CatalogSort,
	dateOf: (item: T) => string | null
): T[] {
	const next = [...items];
	switch (sort) {
		case 'name-desc':
			return next.sort((a, b) => compareNames(b.name, a.name));
		case 'date-asc':
			return next.sort((a, b) => compareDates(dateOf(a), dateOf(b)));
		case 'date-desc':
			return next.sort((a, b) => compareDates(dateOf(b), dateOf(a)));
		default:
			return next.sort((a, b) => compareNames(a.name, b.name));
	}
}

export function catalogCounts(collection: Collection) {
	return {
		locations: collection.locations?.length ?? 0,
		lodging: collection.lodging?.length ?? 0,
		transportations: collection.transportations?.length ?? 0,
		notes: collection.notes?.length ?? 0,
		checklists: collection.checklists?.length ?? 0
	};
}

export function uniqueCategoryNames(collection: Collection): string[] {
	const counts = new Map<string, number>();
	for (const loc of collection.locations ?? []) {
		const name = loc.category?.display_name;
		if (name) counts.set(name, (counts.get(name) ?? 0) + 1);
	}
	return [...counts.entries()]
		.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
		.map(([name]) => name);
}

export function uniqueLodgingTypes(collection: Collection): string[] {
	return [...new Set((collection.lodging ?? []).map((item) => item.type || 'other'))].sort();
}

export function uniqueTransportTypes(collection: Collection): string[] {
	return [
		...new Set((collection.transportations ?? []).map((item) => item.type || 'other'))
	].sort();
}

export function lodgingDateOf(lodging: Lodging): string | null {
	return lodgingDate(lodging);
}

export function transportationDateOf(item: Transportation): string | null {
	return transportationDate(item);
}
