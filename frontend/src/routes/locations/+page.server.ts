import { apiErrorMessage } from '$lib/api';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location } from '$lib/types';

import type { Actions } from '@sveltejs/kit';
import { backendApiUrl, fetchCSRFToken } from '$lib/index.server';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	event.depends('locations:list');

	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let count = 0;
		let adventures: Location[] = [];

		let typeString = event.url.searchParams.get('types');

		// If no type is specified, default to 'all'
		if (!typeString) {
			typeString = 'all';
		}

		const include_collections = event.url.searchParams.get('include_collections') || 'true';
		const requestedOrder = event.url.searchParams.get('order_by') || 'updated_at';
		const order_by = ['updated_at', 'name', 'date', 'rating'].includes(requestedOrder)
			? requestedOrder
			: 'updated_at';
		const order_direction = event.url.searchParams.get('order_direction') || 'asc';
		const page = event.url.searchParams.get('page') || '1';
		const is_visited = event.url.searchParams.get('is_visited') || 'all';

		// The page keeps its own URL parameters; the API takes `ordering` and plain filters.
		// On this page `asc` for updated_at has always meant newest first.
		const descending =
			order_by === 'updated_at' ? order_direction !== 'desc' : order_direction === 'desc';
		const params = new URLSearchParams({ ordering: `${descending ? '-' : ''}${order_by}`, page });
		if (typeString !== 'all') params.set('category', typeString);
		if (is_visited === 'true' || is_visited === 'false') params.set('is_visited', is_visited);
		if (include_collections === 'false') params.set('in_collection', 'false');

		let initialFetch = await event.fetch(backendApiUrl('/api/locations/', params.toString()), {
			headers: {
				Cookie: `sessionid=${event.cookies.get('sessionid')}`
			},
			credentials: 'include'
		});

		if (!initialFetch.ok) {
			let error_message = await initialFetch.json();
			console.error(error_message);
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let visited = res.results as Location[];

			count = res.count;
			adventures = [...adventures, ...visited];
		}

		return {
			props: {
				adventures,
				count,
				order_by,
				order_direction,
				is_visited,
				include_collections
			}
		};
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	image: async (event) => {
		let formData = await event.request.formData();
		let csrfToken = await fetchCSRFToken();
		let sessionId = event.cookies.get('sessionid');
		let res = await fetch(`${serverEndpoint}/api/images/`, {
			method: 'POST',
			headers: {
				Cookie: `csrftoken=${csrfToken}; sessionid=${sessionId}`,
				'X-CSRFToken': csrfToken,
				Referer: event.url.origin // Include Referer header
			},
			body: formData
		});

		// Handle non-JSON responses gracefully (e.g. HTML error pages from backend)
		const contentType = res.headers.get('content-type') || '';
		if (!contentType.includes('application/json')) {
			const text = await res.text();
			console.error(`Image upload failed with status ${res.status}:`, text.substring(0, 200));
			return { error: `Image upload failed (status ${res.status})` };
		}

		let data = await res.json();
		// Callers read `error`; the API's message is `detail`.
		return res.ok
			? data
			: { error: apiErrorMessage(data, `Image upload failed (status ${res.status})`) };
	},
	activity: async (event) => {
		let formData = await event.request.formData();
		let csrfToken = await fetchCSRFToken();
		let sessionId = event.cookies.get('sessionid');
		let res = await fetch(`${serverEndpoint}/api/activities/`, {
			method: 'POST',
			headers: {
				Cookie: `csrftoken=${csrfToken}; sessionid=${sessionId}`,
				'X-CSRFToken': csrfToken,
				Referer: event.url.origin // Include Referer header
			},
			body: formData
		});
		let data = await res.json();
		return res.ok ? data : { error: apiErrorMessage(data, 'Activity upload failed') };
	},
	attachment: async (event) => {
		let formData = await event.request.formData();
		let csrfToken = await fetchCSRFToken();
		let sessionId = event.cookies.get('sessionid');
		let res = await fetch(`${serverEndpoint}/api/attachments/`, {
			method: 'POST',
			headers: {
				Cookie: `csrftoken=${csrfToken}; sessionid=${sessionId}`,
				'X-CSRFToken': csrfToken,
				Referer: event.url.origin // Include Referer header
			},
			body: formData
		});
		let data = await res.json();
		return res.ok ? data : { error: apiErrorMessage(data, 'Attachment upload failed') };
	}
};
