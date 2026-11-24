import { stripMarkdown } from './markdown.js';

export { stripMarkdown };

export type ShareMeta = {
	title: string;
	description: string;
	imageUrl: string;
	pageUrl: string;
};

function formatShortDate(value: string | null | undefined): string {
	if (!value) return '';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return '';
	return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

export function buildCollectionShareMeta(
	collection: {
		id: string;
		name: string;
		description?: string | null;
		is_public?: boolean;
		visibility?: string;
		start_date?: string | null;
		end_date?: string | null;
		locations?: unknown[] | null;
	},
	origin: string
): ShareMeta | null {
	// Only a public story gets a share card; an unlisted link stays out of crawlers.
	const visibility = collection?.visibility ?? (collection?.is_public ? 'public' : 'private');
	if (visibility !== 'public') return null;

	const locCount = collection.locations?.length ?? 0;
	let description = stripMarkdown(collection.description);
	if (!description) {
		const parts: string[] = [];
		if (locCount) {
			parts.push(`${locCount} location${locCount === 1 ? '' : 's'}`);
		}
		const start = formatShortDate(collection.start_date);
		const end = formatShortDate(collection.end_date);
		if (start && end && start !== end) {
			parts.push(`${start} – ${end}`);
		} else if (start) {
			parts.push(start);
		}
		description = parts.join(' · ') || collection.name;
	}

	return {
		title: collection.name,
		description,
		imageUrl: `${origin}/api/collections/${collection.id}/share-image/landscape/`,
		pageUrl: `${origin}/collections/${collection.id}`
	};
}

export function buildLocationShareMeta(
	location: {
		id: string;
		name: string;
		description?: string | null;
		is_public?: boolean;
		location?: string | null;
		rating?: number | null;
		tags?: string[] | null;
		city?: { name?: string } | null;
		region?: { name?: string } | null;
		country?: { name?: string } | null;
	},
	origin: string
): ShareMeta | null {
	if (!location?.is_public) return null;

	let description = stripMarkdown(location.description);
	if (!description) {
		const parts: string[] = [];
		const place =
			location.city?.name ||
			location.region?.name ||
			location.country?.name ||
			location.location ||
			'';
		if (place) parts.push(place);
		if (location.rating != null) parts.push(`Rated ${location.rating}`);
		if (location.tags?.length) parts.push(location.tags.slice(0, 3).join(', '));
		description = parts.join(' · ') || location.name;
	}

	return {
		title: location.name,
		description,
		imageUrl: `${origin}/api/locations/${location.id}/share-image/landscape/`,
		pageUrl: `${origin}/locations/${location.id}`
	};
}
