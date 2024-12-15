import { redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { fetchCSRFToken } from '$lib/index.server';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}
	let csrfToken = await fetchCSRFToken();
	let allActivities: string[] = [];
	let res = await event.fetch(`${endpoint}/api/activity-types/types/`, {
		headers: {
			'X-CSRFToken': csrfToken,
			Cookie: `csrftoken=${csrfToken}`
		},
		credentials: 'include'
	});
	console.log(res);
	let data = await res.json();
	if (data) {
		allActivities = data;
	}
	return {
		props: {
			activities: allActivities
		}
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	getActivities: async (event) => {
		let csrfToken = await fetchCSRFToken();
		let allActivities: string[] = [];
		let res = await fetch(`${endpoint}/api/activity-types/types/`, {
			headers: {
				'X-CSRFToken': csrfToken,
				'Content-Type': 'application/json',
				Cookie: `csrftoken=${csrfToken}`
			}
		});
		console.log(res);
		let data = await res.json();
		if (data) {
			allActivities = data;
		}
		return { activities: allActivities };
	}
};
