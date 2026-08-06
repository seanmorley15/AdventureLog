import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}

	const query = event.url.searchParams.get('q') || event.url.searchParams.get('query');
	const types = event.url.searchParams.get('types') || '';

	if (!query) {
		return {
			query: '',
			results: [],
			facets: {},
			total: 0,
			limit: 20,
			offset: 0,
			error: null
		};
	}

	const sessionId = event.cookies.get('sessionid');
	const params = new URLSearchParams({ q: query, limit: '20', offset: '0' });
	if (types) {
		params.set('types', types);
	}

	const res = await fetch(`${serverEndpoint}/api/search/?${params.toString()}`, {
		headers: {
			'Content-Type': 'application/json',
			Cookie: `sessionid=${sessionId}`
		}
	});

	if (!res.ok) {
		const errorPayload = await res.json().catch(() => ({}));
		return {
			query,
			results: [],
			facets: {},
			total: 0,
			limit: 20,
			offset: 0,
			error: errorPayload.error || 'Failed to fetch search results'
		};
	}

	const data = await res.json();

	return {
		query: data.query,
		results: data.results,
		facets: data.facets,
		total: data.total,
		limit: data.limit,
		offset: data.offset,
		error: null
	};
}) satisfies PageServerLoad;
