import { writable } from 'svelte/store';

export const commandPaletteOpen = writable(false);
export const commandPaletteInitialQuery = writable('');

export function openCommandPalette(initialQuery = '') {
	commandPaletteInitialQuery.set(initialQuery);
	commandPaletteOpen.set(true);
}

export function closeCommandPalette() {
	commandPaletteOpen.set(false);
}

const RECENT_SEARCHES_KEY = 'adventurelog-recent-searches';
const MAX_RECENT_SEARCHES = 5;

export function getRecentSearches(): string[] {
	if (typeof localStorage === 'undefined') return [];
	try {
		const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
		if (!raw) return [];
		const parsed = JSON.parse(raw);
		return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : [];
	} catch {
		return [];
	}
}

export function addRecentSearch(query: string) {
	const normalized = query.trim();
	if (normalized.length < 2 || typeof localStorage === 'undefined') return;

	const recent = getRecentSearches().filter((item) => item !== normalized);
	recent.unshift(normalized);
	localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recent.slice(0, MAX_RECENT_SEARCHES)));
}
