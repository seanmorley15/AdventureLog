import { apiErrorMessage } from '#lib/api/index.js';
import type {
	Location,
	Lodging,
	PlaceSearchResult,
	Recommendation,
	RecommendationResponse
} from '#lib/types.js';
import { googleContentImage } from '#lib/images.js';
import type { RecommendationCategory } from '#lib/recommendations/categories.js';

export type PlacesSearchMeta = {
	provider_used?: string;
	providers_attempted?: string[];
	results: PlaceSearchResult[];
};

export function toPlaceResult(result: Record<string, unknown>): PlaceSearchResult {
	const lat = parseFloat(String(result.lat ?? ''));
	const lng = parseFloat(String(result.lon ?? ''));
	return {
		id: String(result.place_id || `${result.name || 'place'}-${result.lat}-${result.lon}`),
		name: String(result.name ?? ''),
		lat: Number.isFinite(lat) ? lat : 0,
		lng: Number.isFinite(lng) ? lng : 0,
		location: String(result.display_name ?? ''),
		type: result.type ? String(result.type) : undefined,
		category: result.category ? String(result.category) : undefined,
		types: Array.isArray(result.types) ? (result.types as string[]) : [],
		rating: (result.rating as number | null | undefined) ?? null,
		review_count: (result.review_count as number | null | undefined) ?? null,
		photos: Array.isArray(result.photos) ? (result.photos as string[]) : [],
		description: (result.description as string | null | undefined) ?? null,
		website: (result.website as string | null | undefined) ?? null,
		phone_number: (result.phone_number as string | null | undefined) ?? null,
		place_id: (result.place_id as string | null | undefined) ?? null,
		google_maps_url: (result.google_maps_url as string | null | undefined) ?? null,
		powered_by: result.powered_by ? String(result.powered_by) : undefined,
		provider: result.provider
			? String(result.provider)
			: result.powered_by
				? String(result.powered_by)
				: undefined
	};
}

export async function searchPlaces(query: string): Promise<PlacesSearchMeta> {
	const response = await fetch(`/api/places/search/?q=${encodeURIComponent(query)}`);
	const payload = await response.json();
	if (!response.ok) {
		throw new Error(apiErrorMessage(payload, 'Place search failed'));
	}
	return {
		provider_used: payload.provider_used ?? undefined,
		providers_attempted: payload.providers_attempted,
		results: (payload.results ?? []).map((r: Record<string, unknown>) => toPlaceResult(r))
	};
}

export async function fetchPlaceDetails(
	placeId: string,
	name = ''
): Promise<Record<string, unknown>> {
	const response = await fetch(
		`/api/places/details/?place_id=${encodeURIComponent(placeId)}&name=${encodeURIComponent(name)}`
	);
	const details = await response.json();
	if (!response.ok) {
		throw new Error(apiErrorMessage(details, 'Unable to fetch place details'));
	}
	return details;
}

export async function enrichPlace(place: PlaceSearchResult): Promise<PlaceSearchResult> {
	if (!place.place_id) return place;
	try {
		const details = await fetchPlaceDetails(place.place_id, place.name);
		return {
			...place,
			name: String(details.name || place.name),
			location: String(details.formatted_address || place.location),
			types:
				Array.isArray(details.types) && details.types.length > 0
					? (details.types as string[])
					: place.types,
			rating: (details.rating as number | null | undefined) ?? place.rating ?? null,
			review_count:
				(details.review_count as number | null | undefined) ?? place.review_count ?? null,
			description: (details.description as string | null | undefined) ?? place.description ?? null,
			website: (details.website as string | null | undefined) ?? place.website ?? null,
			phone_number:
				(details.phone_number as string | null | undefined) ?? place.phone_number ?? null,
			google_maps_url:
				(details.google_maps_url as string | null | undefined) ?? place.google_maps_url ?? null
		};
	} catch {
		return place;
	}
}

export type FormattedLocationData = {
	city?: { name: string; id: string; visited: boolean };
	region?: { name: string; id: string; visited: boolean };
	country?: { name: string; country_code: string; visited: boolean };
	display_name?: string;
	location_name?: string;
	provider?: string;
};

export async function fetchFormattedLocation(
	lat: number,
	lng: number
): Promise<FormattedLocationData | null> {
	try {
		const response = await fetch(`/api/places/reverse/?lat=${lat}&lon=${lng}`);
		if (!response.ok) {
			return null;
		}

		const data = await response.json();
		const providerUsed = data.provider_used || data.provider || null;
		return {
			city: data.city
				? {
						name: data.city,
						id: data.city_id,
						visited: data.city_visited || false
					}
				: undefined,
			region: data.region
				? {
						name: data.region,
						id: data.region_id,
						visited: data.region_visited || false
					}
				: undefined,
			country: data.country
				? {
						name: data.country,
						country_code: data.country_id,
						visited: false
					}
				: undefined,
			display_name: data.display_name,
			location_name: data.location_name,
			provider: providerUsed
		};
	} catch {
		return null;
	}
}

export function resolveQuickAddLocationLabel(
	formatted: FormattedLocationData | null,
	fallbackLocation = ''
): string {
	return (formatted?.display_name || '').trim() || fallbackLocation.trim() || '';
}

export async function resolveQuickAddPayload(payload: QuickAddPayload): Promise<QuickAddPayload> {
	const formatted = await fetchFormattedLocation(payload.latitude, payload.longitude);
	return {
		...payload,
		location: resolveQuickAddLocationLabel(formatted, payload.location)
	};
}

export type QuickAddPayload = {
	name: string;
	latitude: number;
	longitude: number;
	location: string;
	place_id?: string | null;
	rating?: number | null;
	review_count?: number | null;
	description?: string | null;
	website?: string | null;
	phone_number?: string | null;
	google_maps_url?: string | null;
	types?: string[];
	photos?: string[];
	type?: string;
};

export type QuickAddOptions = {
	collectionId?: string | null;
	/** Also place it on the trip day with this date (YYYY-MM-DD). */
	itineraryDate?: string | null;
};

export type QuickAddResult<T> = T & { quick_add_itinerary_item?: Record<string, unknown> };

async function postQuickAdd<T>(
	endpoint: string,
	payload: QuickAddPayload,
	options: QuickAddOptions,
	failure: string
): Promise<QuickAddResult<T>> {
	const body: Record<string, unknown> = {
		name: payload.name,
		latitude: payload.latitude,
		longitude: payload.longitude,
		location: payload.location,
		place_id: payload.place_id,
		rating: payload.rating,
		review_count: payload.review_count,
		description: payload.description,
		website: payload.website,
		phone_number: payload.phone_number,
		google_maps_url: payload.google_maps_url,
		types: payload.types || [],
		photos: payload.photos || [],
		is_public: false
	};
	if (options.collectionId) body.collection = options.collectionId;
	if (options.itineraryDate) body.itinerary_date = options.itineraryDate;
	if (payload.type) body.type = payload.type;

	const res = await fetch(endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!res.ok) {
		const errorData = await res.json().catch(() => null);
		throw new Error(apiErrorMessage(errorData, failure));
	}
	return res.json();
}

/** `options` may also be a collection id, as older callers pass. */
export function quickAddLocation(
	payload: QuickAddPayload,
	options: QuickAddOptions | string | null = {}
): Promise<QuickAddResult<Location>> {
	const resolved =
		typeof options === 'string' || options === null ? { collectionId: options } : options;
	return postQuickAdd<Location>(
		'/api/locations/quick-add/',
		payload,
		resolved,
		'Failed to create location'
	);
}

export function quickAddLodging(
	payload: QuickAddPayload,
	options: QuickAddOptions = {}
): Promise<QuickAddResult<Lodging>> {
	return postQuickAdd<Lodging>(
		'/api/lodgings/quick-add/',
		payload,
		options,
		'Failed to create lodging'
	);
}

export function placeToQuickAddPayload(place: PlaceSearchResult): QuickAddPayload {
	return {
		name: place.name,
		latitude: place.lat,
		longitude: place.lng,
		location: place.location,
		place_id: place.place_id,
		rating: place.rating,
		review_count: place.review_count,
		description: place.description,
		website: place.website,
		phone_number: place.phone_number,
		google_maps_url: place.google_maps_url,
		types: place.types,
		photos: place.photos,
		type: place.type
	};
}

export function recommendationToQuickAddPayload(rec: Recommendation): QuickAddPayload {
	return {
		name: rec.name,
		latitude: rec.latitude,
		longitude: rec.longitude,
		location: rec.address || rec.description || '',
		place_id: rec.place_id,
		description: rec.description,
		website: rec.website,
		phone_number: rec.phone_number,
		google_maps_url: rec.google_maps_url,
		rating: rec.rating,
		review_count: rec.review_count,
		types: rec.types,
		photos: rec.photos
	};
}

/**
 * A smaller copy of an app Google photo (`/api/places/photo/?...`) for thumbnails.
 * Other addresses are returned unchanged.
 */
export function placePhotoThumbnail(url: string, size = 200): string {
	if (!url.startsWith('/api/places/photo/')) return url;
	const [path, query = ''] = url.split('?');
	const params = new URLSearchParams(query);
	params.set('size', String(size));
	return `${path}?${params.toString()}`;
}

/** Photo URLs to import after save (matches LocationModal quick-start add-details flow). */
export function extractGooglePhotoUrls(
	photos?: string[] | null,
	images?: Array<{ image?: string | null }> | null
): string[] {
	const fromPhotos = (photos ?? []).filter((url) => typeof url === 'string' && url.trim());
	if (fromPhotos.length > 0) {
		return fromPhotos.slice(0, 5);
	}
	return (images ?? [])
		.map((img) => img?.image)
		.filter(
			(url): url is string =>
				typeof url === 'string' && /^(https?:\/\/|\/api\/places\/photo\/)/i.test(url.trim())
		)
		.slice(0, 5);
}

export function placeToLocationPrefill(place: PlaceSearchResult) {
	const photoUrls = extractGooglePhotoUrls(place.photos);
	return {
		id: '',
		name: place.name,
		location: place.location,
		latitude: place.lat,
		longitude: place.lng,
		description: place.description,
		rating: place.rating ?? NaN,
		link: place.website || place.google_maps_url || null,
		tags: place.types?.slice(0, 8) || [],
		photos: photoUrls,
		images: photoUrls.map((url, i) => googleContentImage(`place-${i}`, url, i === 0))
	};
}

export function recommendationToLocationPrefill(rec: Recommendation) {
	const photoUrls = extractGooglePhotoUrls(rec.photos);
	return {
		id: '',
		name: rec.name,
		location: rec.address || rec.description || '',
		latitude: rec.latitude,
		longitude: rec.longitude,
		description: rec.description,
		rating: rec.rating ?? NaN,
		link: rec.website || rec.google_maps_url || null,
		tags: rec.types?.slice(0, 8) || [],
		photos: photoUrls,
		images: photoUrls.map((url, i) => googleContentImage(`rec-${i}`, url, i === 0))
	};
}

/** A `LodgingModal` prefill for a recommendation. */
export function recommendationToLodgingPrefill(
	rec: Recommendation,
	userId: string | null | undefined,
	collectionId: string | null
): Lodging {
	return {
		id: '',
		user: userId ?? '',
		name: rec.name,
		type: '',
		description: rec.description,
		rating: rec.rating,
		link: rec.website || rec.google_maps_url || null,
		check_in: null,
		check_out: null,
		timezone: null,
		reservation_number: null,
		price: null,
		price_currency: null,
		latitude: rec.latitude,
		longitude: rec.longitude,
		location: rec.address || rec.description || null,
		is_public: false,
		collection: collectionId,
		created_at: '',
		updated_at: '',
		images: (rec.photos || []).map((url, i) => googleContentImage(`rec-${i}`, url, i === 0)),
		attachments: []
	} as Lodging;
}

export function nearbyRadiusOptions(isMetric: boolean): { value: number; label: string }[] {
	return isMetric
		? [
				{ value: 1000, label: '1 km' },
				{ value: 2000, label: '2 km' },
				{ value: 5000, label: '5 km' },
				{ value: 10000, label: '10 km' },
				{ value: 20000, label: '20 km' },
				{ value: 50000, label: '50 km' }
			]
		: [
				{ value: 1609, label: '1 mi' },
				{ value: 3219, label: '2 mi' },
				{ value: 8047, label: '5 mi' },
				{ value: 16093, label: '10 mi' },
				{ value: 32187, label: '20 mi' },
				{ value: 80467, label: '50 mi' }
			];
}

export async function fetchRecommendations(params: {
	lat: number;
	lon: number;
	radius: number;
	category: RecommendationCategory;
	limit?: number;
}): Promise<RecommendationResponse> {
	const searchParams = new URLSearchParams({
		lat: params.lat.toString(),
		lon: params.lon.toString(),
		radius: params.radius.toString(),
		category: params.category
	});
	if (params.limit) searchParams.set('limit', String(params.limit));
	const response = await fetch(`/api/recommendations/?${searchParams.toString()}`);
	const data = await response.json();
	if (!response.ok) {
		throw new Error(apiErrorMessage(data, 'Failed to fetch recommendations'));
	}
	return data as RecommendationResponse;
}

export async function refetchPins(): Promise<import('#lib/types.js').Pin[]> {
	const response = await fetch('/api/locations/pins/');
	if (!response.ok) return [];
	return response.json();
}

export function formatProviderLabel(provider?: string | null): string | null {
	const normalized = (provider || '').trim().toLowerCase();
	if (!normalized) return null;
	if (normalized === 'google') return 'Google Maps';
	if (normalized === 'osm' || normalized === 'nominatim') return 'OpenStreetMap';
	if (normalized === 'mixed') return 'Google Maps + OpenStreetMap';
	if (normalized === 'google+wikipedia') return 'Google Maps + Wikipedia';
	if (normalized === 'wikipedia') return 'Wikipedia';
	return provider || null;
}
