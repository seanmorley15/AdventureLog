import type { Category } from '#lib/types.js';

const STORAGE_KEY = 'adventurelog:place-category';

function load(): Category | null {
	if (typeof localStorage === 'undefined') return null;
	try {
		const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
		return stored && typeof stored.name === 'string' ? (stored as Category) : null;
	} catch {
		return null;
	}
}

/**
 * The category the user last filed a searched place under. Adding places to a trip one after
 * another then takes a single click each, and every place-adding surface shares the choice.
 */
class PlaceCategoryStore {
	#value = $state<Category | null>(load());

	get current(): Category | null {
		return this.#value;
	}

	set current(category: Category | null) {
		this.#value = category;
		if (typeof localStorage === 'undefined') return;
		try {
			if (category) localStorage.setItem(STORAGE_KEY, JSON.stringify(category));
			else localStorage.removeItem(STORAGE_KEY);
		} catch {
			// Storage can be full or blocked; the choice then lasts for this page only.
		}
	}
}

export const placeCategory = new PlaceCategoryStore();
