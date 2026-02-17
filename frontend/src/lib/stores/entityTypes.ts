import { writable, derived, get } from 'svelte/store';
import { TRANSPORTATION_TYPES_ICONS, LODGING_TYPES_ICONS } from '$lib';

export interface EntityType {
	id: number;
	key: string;
	name: string;
	icon: string;
	display_order: number;
}

export interface ActivityEntityType extends EntityType {
	color: string;
}

// Stores for the types
export const transportationTypes = writable<EntityType[]>([]);
export const lodgingTypes = writable<EntityType[]>([]);
export const adventureTypes = writable<EntityType[]>([]); // For collection categories
export const activityTypes = writable<ActivityEntityType[]>([]); // For sports/activities

// Loading state
export const typesLoading = writable(false);
export const typesLoaded = writable(false);

// Derived stores for icon lookup
export const transportationTypesIcons = derived(transportationTypes, ($types) => {
	const icons: Record<string, string> = {};
	for (const type of $types) {
		icons[type.key] = type.icon;
	}
	return icons;
});

export const lodgingTypesIcons = derived(lodgingTypes, ($types) => {
	const icons: Record<string, string> = {};
	for (const type of $types) {
		icons[type.key] = type.icon;
	}
	return icons;
});

export const adventureTypesIcons = derived(adventureTypes, ($types) => {
	const icons: Record<string, string> = {};
	for (const type of $types) {
		icons[type.key] = type.icon;
	}
	return icons;
});

export const activityTypesIcons = derived(activityTypes, ($types) => {
	const icons: Record<string, string> = {};
	for (const type of $types) {
		icons[type.key] = type.icon;
	}
	return icons;
});

// Fetch all entity types from the API
export async function fetchEntityTypes(): Promise<void> {
	// Skip if already loaded or loading
	if (get(typesLoaded) || get(typesLoading)) {
		return;
	}

	typesLoading.set(true);

	try {
		const [transportRes, lodgingRes, adventureRes, activityRes] = await Promise.all([
			fetch('/api/transportation-types/'),
			fetch('/api/lodging-types/'),
			fetch('/api/adventure-types/'),
			fetch('/api/activity-types/')
		]);

		if (transportRes.ok) {
			const data = await transportRes.json();
			transportationTypes.set(data);
		}

		if (lodgingRes.ok) {
			const data = await lodgingRes.json();
			lodgingTypes.set(data);
		}

		if (adventureRes.ok) {
			const data = await adventureRes.json();
			adventureTypes.set(data);
		}

		if (activityRes.ok) {
			const data = await activityRes.json();
			activityTypes.set(data);
		}

		typesLoaded.set(true);
	} catch (error) {
		console.error('Error fetching entity types:', error);
	} finally {
		typesLoading.set(false);
	}
}

// Helper to get icon for a transportation type (store first, then hardcoded fallback)
export function getTransportationIcon(typeKey: string | null | undefined): string {
	if (!typeKey) return '🚗';
	const types = get(transportationTypes);
	const type = types.find((t) => t.key === typeKey);
	if (type?.icon) return type.icon;
	if (typeKey in TRANSPORTATION_TYPES_ICONS) {
		return TRANSPORTATION_TYPES_ICONS[typeKey as keyof typeof TRANSPORTATION_TYPES_ICONS];
	}
	return '🚗';
}

// Helper to get icon for a lodging type (store first, then hardcoded fallback)
export function getLodgingIcon(typeKey: string | null | undefined): string {
	if (!typeKey) return '🏨';
	const types = get(lodgingTypes);
	const type = types.find((t) => t.key === typeKey);
	if (type?.icon) return type.icon;
	if (typeKey in LODGING_TYPES_ICONS) {
		return LODGING_TYPES_ICONS[typeKey as keyof typeof LODGING_TYPES_ICONS];
	}
	return '🏨';
}

// Helper to get icon for an adventure type (collection category)
export function getAdventureIcon(typeKey: string | null | undefined): string {
	const types = get(adventureTypes);
	const type = types.find((t) => t.key === typeKey);
	return type?.icon || '🌍';
}

// Helper to get icon for an activity/sport type
export function getActivityIcon(typeKey: string | null | undefined): string {
	const types = get(activityTypes);
	const type = types.find((t) => t.key === typeKey);
	return type?.icon || '🏃';
}

// Helper to get color for an activity/sport type
export function getActivityColor(typeKey: string | null | undefined): string {
	const types = get(activityTypes);
	const type = types.find((t) => t.key === typeKey);
	return type?.color || '#6B7280';
}
