import type {
	Location,
	PlaceSearchResult,
	Recommendation,
	RecommendationResponse
} from '$lib/types';

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
	const response = await fetch(
		`/api/places/search/?query=${encodeURIComponent(query)}&include_meta=1`
	);
	const payload = await response.json();
	if (!response.ok) {
		throw new Error(payload?.error || 'Place search failed');
	}
	const rawResults = Array.isArray(payload) ? payload : payload?.results || [];
	const provider_used = Array.isArray(payload) ? undefined : payload?.provider_used;
	return {
		provider_used,
		providers_attempted: payload?.providers_attempted,
		results: Array.isArray(rawResults) ? rawResults.map((r) => toPlaceResult(r)) : []
	};
}

export async function fetchPlaceDetails(
	placeId: string,
	name = ''
): Promise<Record<string, unknown>> {
	const response = await fetch(
		`/api/places/place_details/?place_id=${encodeURIComponent(placeId)}&name=${encodeURIComponent(name)}`
	);
	const details = await response.json();
	if (!response.ok) {
		throw new Error(details?.error || 'Unable to fetch place details');
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

export async function quickAddLocation(payload: QuickAddPayload): Promise<Location> {
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
	if (payload.type) body.type = payload.type;

	const res = await fetch('/api/locations/quick-add/', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!res.ok) {
		const errorData = await res.json().catch(() => ({}));
		throw new Error(
			(errorData as { error?: string; detail?: string })?.error ||
				(errorData as { detail?: string })?.detail ||
				'Failed to create location'
		);
	}
	return res.json();
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
		.filter((url): url is string => typeof url === 'string' && /^https?:\/\//i.test(url.trim()))
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
		images: photoUrls.map((url, i) => ({
			id: `place-${i}`,
			image: url,
			is_primary: i === 0,
			immich_id: null
		}))
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
		images: photoUrls.map((url, i) => ({
			id: `rec-${i}`,
			image: url,
			is_primary: i === 0,
			immich_id: null
		}))
	};
}

export async function fetchRecommendations(params: {
	lat: number;
	lon: number;
	radius: number;
	category: 'tourism' | 'food' | 'lodging';
}): Promise<RecommendationResponse> {
	const searchParams = new URLSearchParams({
		lat: params.lat.toString(),
		lon: params.lon.toString(),
		radius: params.radius.toString(),
		category: params.category
	});
	const response = await fetch(`/api/recommendations/query/?${searchParams.toString()}`);
	const data: RecommendationResponse = await response.json();
	if (!response.ok) {
		throw new Error(data.error || 'Failed to fetch recommendations');
	}
	if (data.error) {
		throw new Error(data.error);
	}
	return data;
}

export async function refetchPins(): Promise<import('$lib/types').Pin[]> {
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
