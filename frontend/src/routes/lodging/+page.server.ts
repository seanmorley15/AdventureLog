import { redirect } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Lodging } from '$lib/types';
import { fetchCSRFToken } from '$lib/index.server';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let count = 0;
		let lodgingItems: Lodging[] = [];

		let typeString = event.url.searchParams.get('types');

		// If no type is specified, default to 'all'
		if (!typeString) {
			typeString = 'all';
		}

		const order_by = event.url.searchParams.get('order_by') || 'updated_at';
		const order_direction = event.url.searchParams.get('order_direction') || 'asc';
		const page = event.url.searchParams.get('page') || '1';
		const is_visited = event.url.searchParams.get('is_visited') || 'all';
		const is_public = event.url.searchParams.get('is_public') || 'all';
		const ownership = event.url.searchParams.get('ownership') || 'all';
		const min_rating = event.url.searchParams.get('min_rating') || 'all';
		const include_collections = event.url.searchParams.get('include_collections') || 'true';

		let initialFetch = await event.fetch(
			`${serverEndpoint}/api/lodging/filtered?types=${typeString}&order_by=${order_by}&order_direction=${order_direction}&page=${page}&is_visited=${is_visited}&is_public=${is_public}&ownership=${ownership}&min_rating=${min_rating}&include_collections=${include_collections}`,
			{
				headers: {
					Cookie: `sessionid=${event.cookies.get('sessionid')}`
				},
				credentials: 'include'
			}
		);

		if (!initialFetch.ok) {
			let error_message = await initialFetch.json();
			console.error(error_message);
			console.error('Failed to fetch lodging');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let results = res.results as Lodging[];

			count = res.count;
			lodgingItems = [...lodgingItems, ...results];
		}

		return {
			props: {
				lodgingItems,
				count
			}
		};
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	activity: async (event) => {
		let formData = await event.request.formData();
		let csrfToken = await fetchCSRFToken();
		let sessionId = event.cookies.get('sessionid');
		let res = await fetch(`${serverEndpoint}/api/activities/`, {
			method: 'POST',
			headers: {
				Cookie: `csrftoken=${csrfToken}; sessionid=${sessionId}`,
				'X-CSRFToken': csrfToken,
				Referer: event.url.origin
			},
			body: formData
		});
		let data = await res.json();
		return data;
	}
};
