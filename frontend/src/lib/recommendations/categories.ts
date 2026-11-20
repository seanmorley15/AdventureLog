/** The categories `/api/recommendations/` understands, in display order. */
export const RECOMMENDATION_CATEGORIES = [
	{ key: 'attractions', labelKey: 'recomendations.attractions', emoji: '🏛️', isLodging: false },
	{ key: 'culture', labelKey: 'recomendations.culture', emoji: '🎭', isLodging: false },
	{ key: 'nature', labelKey: 'recomendations.nature', emoji: '🌲', isLodging: false },
	{ key: 'food', labelKey: 'recomendations.food', emoji: '🍴', isLodging: false },
	{ key: 'nightlife', labelKey: 'recomendations.nightlife', emoji: '☕', isLodging: false },
	{ key: 'lodging', labelKey: 'recomendations.lodging', emoji: '🏨', isLodging: true },
	{ key: 'activities', labelKey: 'recomendations.activities', emoji: '🎡', isLodging: false }
] as const;

export type RecommendationCategory = (typeof RECOMMENDATION_CATEGORIES)[number]['key'];

export function categoryMeta(key: RecommendationCategory) {
	return RECOMMENDATION_CATEGORIES.find((c) => c.key === key) ?? RECOMMENDATION_CATEGORIES[0];
}

const LODGING_TYPES = new Set([
	'lodging',
	'hotel',
	'hostel',
	'motel',
	'guest_house',
	'resort_hotel',
	'bed_and_breakfast',
	'campground',
	'camp_site',
	'inn'
]);

/** Whether a result can sensibly be saved as lodging. */
export function isLodgingRecommendation(rec: { category?: string; types?: string[] }): boolean {
	if (rec.category === 'lodging') return true;
	return (rec.types ?? []).some((type) => LODGING_TYPES.has(type));
}
