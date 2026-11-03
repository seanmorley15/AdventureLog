import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Lodging } from '#lib/types.js';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/lodgings/${id.id}/`, {
		headers: {
			Cookie: `sessionid=${event.cookies.get('sessionid')}`
		},
		credentials: 'include'
	});
	if (!request.ok) {
		console.error('Failed to fetch lodging ' + id.id);
		return {
			props: {
				lodging: null
			}
		};
	} else {
		let lodging = (await request.json()) as Lodging;

		return {
			props: {
				lodging
			}
		};
	}
}) satisfies PageServerLoad;
