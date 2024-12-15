import { redirect } from '@sveltejs/kit';
import type { PageServerLoad, RequestEvent } from '../$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

export const load: PageServerLoad = async (event: RequestEvent) => {
	const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
	if (!event.locals.user || !event.cookies.get('sessionid')) {
		return redirect(302, '/login');
	}

	let sessionId = event.cookies.get('sessionid');
	let stats = null;

	let res = await event.fetch(`${endpoint}/api/stats/counts/`, {
		headers: {
			Cookie: `sessionid=${sessionId}`
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
