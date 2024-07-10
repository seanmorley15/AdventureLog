import { redirect } from '@sveltejs/kit';
import type { PageServerLoad, RequestEvent } from '../$types';
import { PUBLIC_SERVER_URL } from '$env/static/public';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
export const load: PageServerLoad = async (event: RequestEvent) => {
	if (!event.locals.user || !event.cookies.get('auth')) {
		return redirect(302, '/login');
	}

	let stats = null;

	let res = await event.fetch(`${endpoint}/api/stats/counts/`, {
		headers: {
			Cookie: `${event.cookies.get('auth')}`
		}
	});
	if (!res.ok) {
		console.error('Failed to fetch user stats');
	} else {
		stats = await res.json();
	}

	return {
		user: event.locals.user,
		stats
	};
};
