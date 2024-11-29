const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Country } from '$lib/types';
import { redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { fetchCSRFToken } from '$lib/index.server';

const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		const res = await event.fetch(`${endpoint}/api/countries/`, {
			method: 'GET',
			headers: {
				Cookie: `sessionid=${event.cookies.get('sessionid')}`
			},
			credentials: 'include'
		});
		if (!res.ok) {
			console.error('Failed to fetch countries');
			return { status: 500 };
		} else {
			const countries = (await res.json()) as Country[];
			return {
				props: {
					countries
				}
			};
		}
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	markVisited: async (event) => {
		const body = await event.request.json();

		if (!body || !body.regionId) {
			return {
				status: 400
			};
		}

		let sessionId = event.cookies.get('sessionid');

		if (!event.locals.user || !sessionId) {
			return redirect(302, '/login');
		}

		let csrfToken = await fetchCSRFToken();

		const res = await fetch(`${endpoint}/api/visitedregion/`, {
			method: 'POST',
			headers: {
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken
			},
			body: JSON.stringify({ region: body.regionId })
		});

		if (!res.ok) {
			console.error('Failed to mark country as visited');
			return { status: 500 };
		} else {
			return {
				status: 200,
				data: await res.json()
			};
		}
	},
	removeVisited: async (event) => {
		const body = await event.request.json();

		if (!body || !body.visitId) {
			return {
				status: 400
			};
		}

		const visitId = body.visitId as number;

		let sessionId = event.cookies.get('sessionid');

		if (!event.locals.user || !sessionId) {
			return redirect(302, '/login');
		}

		let csrfToken = await fetchCSRFToken();

		const res = await fetch(`${endpoint}/api/visitedregion/${visitId}/`, {
			method: 'DELETE',
			headers: {
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken
			}
		});

		if (res.status !== 204) {
			console.error('Failed to remove country from visited');
			return { status: 500 };
		} else {
			return {
				status: 200
			};
		}
	}
};
