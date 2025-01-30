import { redirect, error } from '@sveltejs/kit';
import type { PageServerLoad, RequestEvent } from '../../$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

export const load: PageServerLoad = async (event: RequestEvent) => {
	const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

	let uuid = event.params.uuid as string;

	if (!uuid) {
		return error(404, 'Not found');
	}

	// let sessionId = event.cookies.get('sessionid');
	// let stats = null;

	// let res = await event.fetch(`${endpoint}/api/stats/counts/`, {
	// 	headers: {
	// 		Cookie: `sessionid=${sessionId}`
	// 	}
	// });
	// if (!res.ok) {
	// 	console.error('Failed to fetch user stats');
	// } else {
	// 	stats = await res.json();
	// }

	let userData = await event.fetch(`${endpoint}/auth/user/${uuid}/`);
	if (!userData.ok) {
		return error(404, 'Not found');
	}

	let data = await userData.json();

	return {
		user: data.user,
		adventures: data.adventures,
		collections: data.collections
	};
};
