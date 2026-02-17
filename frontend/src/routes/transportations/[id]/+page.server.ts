import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const COLLABORATIVE_MODE = process.env['COLLABORATIVE_MODE'] === 'true';
import type { AdditionalTransportation } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/transportations/${id.id}/additional-info/`, {
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
			},
			collaborativeMode: COLLABORATIVE_MODE
		};
	} else {
		let transportation = (await request.json()) as AdditionalTransportation;

		return {
			props: {
				transportation
			},
			collaborativeMode: COLLABORATIVE_MODE
		};
	}
}) satisfies PageServerLoad;
