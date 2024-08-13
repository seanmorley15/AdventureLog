import { redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}
	let allActivities: string[] = [];
	let res = await fetch(`${endpoint}/api/activity-types/types/`, {
		headers: {
			'Content-Type': 'application/json',
			Cookie: `${event.cookies.get('auth')}`
		}
	});
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
		let allActivities: string[] = [];
		let res = await fetch(`${endpoint}/api/activity-types/types/`, {
			headers: {
				'Content-Type': 'application/json',
				Cookie: `${event.cookies.get('auth')}`
			}
		});
		let data = await res.json();
		if (data) {
			allActivities = data;
		}
		return { activities: allActivities };
	}
};
