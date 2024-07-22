import type { Adventure } from '$lib/types';
import type { PageServerLoad } from './$types';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	// get url param query
	const query = event.url.searchParams.get('query');

	if (!query) {
		return { data: [] };
	}

	let res = await fetch(`${serverEndpoint}/api/adventures/search/?query=${query}`, {
		headers: {
			'Content-Type': 'application/json',
			Cookie: `${event.cookies.get('auth')}`
		}
	});

	if (res.ok) {
		let data = await res.json();
		console.log('Search data:', data);

		return {
			props: {
				adventures: data,
				query
			}
		};
	} else {
		console.error('Failed to fetch search data');
		let error = await res.json();
		return { error: error.error };
	}
}) satisfies PageServerLoad;
