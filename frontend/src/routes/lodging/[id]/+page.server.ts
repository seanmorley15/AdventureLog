import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const COLLABORATIVE_MODE = process.env['COLLABORATIVE_MODE'] === 'true';
import type { AdditionalLodging } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/lodging/${id.id}/additional-info/`, {
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
			},
			collaborativeMode: COLLABORATIVE_MODE
		};
	} else {
		let lodging = (await request.json()) as AdditionalLodging;

		return {
			props: {
				lodging
			},
			collaborativeMode: COLLABORATIVE_MODE
		};
	}
}) satisfies PageServerLoad;
