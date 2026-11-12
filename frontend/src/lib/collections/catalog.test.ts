import { describe, expect, it } from 'vitest';
import type { Location } from '#lib/types.js';
import { CatalogFilters, locationMatches } from './catalog.svelte';

function place(name: string, rating: number | null): Location {
	return { id: name, name, rating, visits: [], is_visited: false } as unknown as Location;
}

// #1234: a trip full of suggestions can be narrowed to the best-rated places.
describe('minimum rating filter', () => {
	it('shows every place when no minimum is set', () => {
		const filters = new CatalogFilters();
		expect([place('a', 3), place('b', null)].every((p) => locationMatches(p, filters))).toBe(true);
	});

	it('keeps places rated at or above the minimum', () => {
		const filters = new CatalogFilters();
		filters.minRating = 4;
		expect(locationMatches(place('four', 4), filters)).toBe(true);
		expect(locationMatches(place('four and a half', 4.5), filters)).toBe(true);
		expect(locationMatches(place('three', 3), filters)).toBe(false);
	});

	it('hides unrated places while a minimum is set', () => {
		const filters = new CatalogFilters();
		filters.minRating = 1;
		expect(locationMatches(place('unrated', null), filters)).toBe(false);
	});

	it('counts as a change to the filters and is cleared by reset', () => {
		const filters = new CatalogFilters();
		filters.minRating = 5;
		expect(filters.isPristine()).toBe(false);
		filters.reset();
		expect(filters.minRating).toBeNull();
		expect(filters.isPristine()).toBe(true);
	});
});
