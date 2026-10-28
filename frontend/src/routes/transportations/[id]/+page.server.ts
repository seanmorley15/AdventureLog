import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Transportation } from '#lib/types.js';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/transportations/${id.id}/`, {
		headers: {
			Cookie: `sessionid=${event.cookies.get('sessionid')}`
		},
		credentials: 'include'
	});
	if (!request.ok) {
		console.error('Failed to fetch transportation ' + id.id);
		return {
			props: {
				transportation: null
			}
		};
	} else {
		let transportation = (await request.json()) as Transportation;

		return {
			props: {
				transportation
			}
		};
	}
}) satisfies PageServerLoad;
