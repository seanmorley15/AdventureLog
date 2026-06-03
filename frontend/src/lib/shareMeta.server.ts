const MARKDOWN_PATTERNS: Array<[RegExp, string]> = [
	[/!\[.*?\]\(.*?\)/g, ''],
	[/\[([^\]]+)\]\([^)]+\)/g, '$1'],
	[/#{1,6}\s*/g, ''],
	[/\*\*([^*]+)\*\*/g, '$1'],
	[/\*([^*]+)\*/g, '$1'],
	[/`([^`]+)`/g, '$1'],
];

export function stripMarkdown(value: string | null | undefined, maxLength = 200): string {
	if (!value) return '';
	let text = String(value);
	for (const [pattern, replacement] of MARKDOWN_PATTERNS) {
		text = text.replace(pattern, replacement);
	}
	text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
	text = text.replace(/\n{3,}/g, '\n\n').trim();
	if (text.length > maxLength) {
		return `${text.slice(0, maxLength - 3)}...`;
	}
	return text;
}

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
		start_date?: string | null;
		end_date?: string | null;
		locations?: unknown[] | null;
	},
	origin: string
): ShareMeta | null {
	if (!collection?.is_public) return null;

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
		pageUrl: `${origin}/collections/${collection.id}`,
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
		pageUrl: `${origin}/locations/${location.id}`,
	};
}
