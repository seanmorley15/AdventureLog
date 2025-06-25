import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}

	const query = event.url.searchParams.get('query');

	if (!query) {
		return { data: [] };
	}

	let sessionId = event.cookies.get('sessionid');

	let res = await fetch(`${serverEndpoint}/api/search/?query=${query}`, {
		headers: {
			'Content-Type': 'application/json',
			Cookie: `sessionid=${sessionId}`
		}
	});

	if (!res.ok) {
		console.error('Failed to fetch search data');
		let error = await res.json();
		return { error: error.error };
	}

	let data = await res.json();

	return {
		locations: data.locations,
		collections: data.collections,
		users: data.users,
		countries: data.countries,
		regions: data.regions,
		cities: data.cities,
		visited_cities: data.visited_cities,
		visited_regions: data.visited_regions
	};
}) satisfies PageServerLoad;
