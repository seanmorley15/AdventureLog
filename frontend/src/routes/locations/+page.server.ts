import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location } from '$lib/types';

import type { Actions } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
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
		const order_by = event.url.searchParams.get('order_by') || 'updated_at';
		const order_direction = event.url.searchParams.get('order_direction') || 'asc';
		const page = event.url.searchParams.get('page') || '1';
		const is_visited = event.url.searchParams.get('is_visited') || 'all';

		let initialFetch = await event.fetch(
			`${serverEndpoint}/api/locations/filtered?types=${typeString}&order_by=${order_by}&order_direction=${order_direction}&include_collections=${include_collections}&page=${page}&is_visited=${is_visited}`,
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
				count
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
		let data = await res.json();
		return data;
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
		return data;
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

		console.log(res);
		console.log(data);
		return data;
	}
};
