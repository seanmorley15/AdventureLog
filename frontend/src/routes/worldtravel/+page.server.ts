const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Country } from '$lib/types';
import { redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		const res = await fetch(`${endpoint}/api/countries/`, {
			method: 'GET',
			headers: {
				Cookie: `${event.cookies.get('auth')}`
			}
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

	return {};
}) satisfies PageServerLoad;

export const actions: Actions = {
	markVisited: async (event) => {
		const body = await event.request.json();

		if (!body || !body.regionId) {
			return {
				status: 400
			};
		}

		if (!event.locals.user || !event.cookies.get('auth')) {
			return redirect(302, '/login');
		}

		const res = await fetch(`${endpoint}/api/visitedregion/`, {
			method: 'POST',
			headers: {
				Cookie: `${event.cookies.get('auth')}`,
				'Content-Type': 'application/json'
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

		if (!event.locals.user || !event.cookies.get('auth')) {
			return redirect(302, '/login');
		}

		const res = await fetch(`${endpoint}/api/visitedregion/${visitId}/`, {
			method: 'DELETE',
			headers: {
				Cookie: `${event.cookies.get('auth')}`,
				'Content-Type': 'application/json'
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
