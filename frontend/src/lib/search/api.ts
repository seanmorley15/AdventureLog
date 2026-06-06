import type { SearchEntityType, SearchResponse } from './types';

export type SearchAppOptions = {
	types?: SearchEntityType[];
	limit?: number;
	offset?: number;
	signal?: AbortSignal;
};

export async function searchApp(
	query: string,
	options: SearchAppOptions = {}
): Promise<SearchResponse> {
	const params = new URLSearchParams({ q: query });

	if (options.types?.length) {
		params.set('types', options.types.join(','));
	}
	if (options.limit != null) {
		params.set('limit', String(options.limit));
	}
	if (options.offset != null) {
		params.set('offset', String(options.offset));
	}

	const response = await fetch(`/api/search/?${params.toString()}`, {
		signal: options.signal
	});
	const payload = await response.json();

	if (!response.ok) {
		throw new Error(payload?.error || 'Search failed');
	}

	return payload as SearchResponse;
}
