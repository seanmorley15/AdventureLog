const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Country, Region, VisitedRegion } from '$lib/types';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params.id.toUpperCase();

	let regions: Region[] = [];
	let visitedRegions: VisitedRegion[] = [];
	let country: Country;

	let sessionId = event.cookies.get('sessionid');

	if (!sessionId) {
		return redirect(302, '/login');
	}

	let res = await fetch(`${endpoint}/api/${id}/regions/`, {
		method: 'GET',
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	if (!res.ok) {
		console.error('Failed to fetch regions');
		return redirect(302, '/404');
	} else {
		regions = (await res.json()) as Region[];
	}

	res = await fetch(`${endpoint}/api/${id}/visits/`, {
		method: 'GET',
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	if (!res.ok) {
		console.error('Failed to fetch visited regions');
		return { status: 500 };
	} else {
		visitedRegions = (await res.json()) as VisitedRegion[];
	}

	res = await fetch(`${endpoint}/api/countries/${regions[0].country}/`, {
		method: 'GET',
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	if (!res.ok) {
		console.error('Failed to fetch country');
		return { status: 500 };
	} else {
		country = (await res.json()) as Country;
	}

	// Attempt to fetch a short description (Wikipedia/Wikidata generated) for the country
	let description: string | null = null;
	try {
		const descRes = await fetch(
			`${endpoint}/api/generate/desc/?name=${encodeURIComponent(country.name)}`,
			{
				method: 'GET',
				headers: {
					Cookie: `sessionid=${sessionId}`
				}
			}
		);
		if (descRes.ok) {
			const descJson = await descRes.json();
			if (descJson && typeof descJson.extract === 'string') {
				description = descJson.extract;
			}
		} else {
			console.debug('No description available for', country.name);
		}
	} catch (e) {
		console.debug('Failed to fetch description:', e);
	}

	return {
		props: {
			regions,
			visitedRegions,
			country,
			description
		}
	};
}) satisfies PageServerLoad;
