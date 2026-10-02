const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { City, Region, VisitedCity } from '$lib/types';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params.id.toUpperCase();
	const sessionId = event.cookies.get('sessionid');

	if (!sessionId) {
		return redirect(302, '/login');
	}

	const headers = {
		Cookie: `sessionid=${sessionId}`
	};

	const [citiesRes, regionRes, visitsRes] = await Promise.all([
		fetch(`${endpoint}/api/regions/${id}/cities/`, { method: 'GET', headers }),
		fetch(`${endpoint}/api/regions/${id}/`, { method: 'GET', headers }),
		fetch(`${endpoint}/api/regions/${id}/cities/visits/`, { method: 'GET', headers })
	]);

	if (!citiesRes.ok) {
		console.error('Failed to fetch regions');
		return redirect(302, '/404');
	}

	if (!regionRes.ok) {
		console.error('Failed to fetch country');
		return { status: 500 };
	}

	if (!visitsRes.ok) {
		console.error('Failed to fetch visited regions');
		return { status: 500 };
	}

	const cities = (await citiesRes.json()) as City[];
	const region = (await regionRes.json()) as Region;
	const visitedCities = (await visitsRes.json()) as VisitedCity[];

	return {
		props: {
			cities,
			region,
			visitedCities,
			description: null as string | null
		}
	};
}) satisfies PageServerLoad;
