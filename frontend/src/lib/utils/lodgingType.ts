const LODGING_TYPE_MAP: Record<string, string> = {
	hotel: 'hotel',
	resort_hotel: 'resort',
	motel: 'motel',
	hostel: 'hostel',
	bed_and_breakfast: 'bnb',
	guest_house: 'bnb',
	campground: 'campground',
	rv_park: 'campground',
	camping_cabin: 'cabin',
	apartment_building: 'apartment',
	lodging: 'hotel',
	villa: 'villa'
};

const VALID_TYPES = new Set([
	'hotel',
	'hostel',
	'resort',
	'bnb',
	'campground',
	'cabin',
	'apartment',
	'house',
	'villa',
	'motel',
	'other'
]);

export function inferLodgingTypeFromPlace(primaryType: unknown, placeTypes: unknown): string {
	if (typeof primaryType === 'string') {
		const normalized = primaryType.trim().toLowerCase();
		if (VALID_TYPES.has(normalized)) {
			return normalized;
		}
	}

	const normalizedTypes = Array.isArray(placeTypes)
		? placeTypes
				.map((typeName) => (typeof typeName === 'string' ? typeName.trim().toLowerCase() : ''))
				.filter(Boolean)
		: [];

	for (const typeName of normalizedTypes) {
		if (LODGING_TYPE_MAP[typeName]) {
			return LODGING_TYPE_MAP[typeName];
		}
	}

	for (const typeName of normalizedTypes) {
		if (VALID_TYPES.has(typeName)) {
			return typeName;
		}
	}

	return 'other';
}
