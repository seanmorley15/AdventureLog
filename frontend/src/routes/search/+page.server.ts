import type { Adventure, OpenStreetMapPlace } from '$lib/types';
import { fail } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { appVersion } from '$lib/config';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const query = event.url.searchParams.get('query');
	const property = event.url.searchParams.get('property') || 'all';

	if (!query) {
		return { data: [] };
	}

	let res = await fetch(
		`${serverEndpoint}/api/adventures/search/?query=${query}&property=${property}`,
		{
			headers: {
				'Content-Type': 'application/json',
				Cookie: `${event.cookies.get('auth')}`
			}
		}
	);

	if (!res.ok) {
		console.error('Failed to fetch search data');
		let error = await res.json();
		return { error: error.error };
	}

	let adventures: Adventure[] = await res.json();

	let osmRes = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`, {
		headers: {
			'User-Agent': `AdventureLog / ${appVersion} `
		}
	});

	if (!osmRes.ok) {
		console.error('Failed to fetch OSM data');
		let error = await res.json();
		return { error: error.error };
	}

	let osmData = (await osmRes.json()) as OpenStreetMapPlace[];

	return {
		props: {
			adventures,
			query,
			osmData
		}
	};
}) satisfies PageServerLoad;
