import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const POST: RequestHandler = async (event) => {
	let allActivities: string[] = [];
	let csrfToken = await fetchCSRFToken();
	let sessionId = event.cookies.get('sessionid');
	let res = await event.fetch(`${endpoint}/api/tags/types/`, {
		headers: {
			'X-CSRFToken': csrfToken,
			Cookie: `csrftoken=${csrfToken}; sessionid=${sessionId}`
		},
		credentials: 'include'
	});
	let data = await res.json();
	if (data) {
		allActivities = data;
	}
	return json({ activities: allActivities });
};
