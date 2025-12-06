const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { City, Country, Region, VisitedCity, VisitedRegion } from '$lib/types';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params.id.toUpperCase();

	let cities: City[] = [];
	let region = {} as Region;
	let visitedCities: VisitedCity[] = [];

	let sessionId = event.cookies.get('sessionid');

	if (!sessionId) {
		return redirect(302, '/login');
	}

	let res = await fetch(`${endpoint}/api/regions/${id}/cities/`, {
		method: 'GET',
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	if (!res.ok) {
		console.error('Failed to fetch regions');
		return redirect(302, '/404');
	} else {
		cities = (await res.json()) as City[];
	}

	res = await fetch(`${endpoint}/api/regions/${id}/`, {
		method: 'GET',
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	if (!res.ok) {
		console.error('Failed to fetch country');
		return { status: 500 };
	} else {
		region = (await res.json()) as Region;
	}

	// Fetch country details (if available) to improve description search
	let country: Country | null = null;
	if (region?.country) {
		res = await fetch(`${endpoint}/api/countries/${region.country}/`, {
			method: 'GET',
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		});
		if (res.ok) {
			country = (await res.json()) as Country;
		} else {
			console.debug('Failed to fetch country for region description');
		}
	}

	// Attempt to fetch a short description (Wikipedia/Wikidata generated) for the region.
	// Try multiple candidate queries to improve the chance of a match: region name, "region, country", then country name.
	let description: string | null = null;
	try {
		const candidates: string[] = [];
		if (region?.name) candidates.push(region.name);
		if (region?.name && country?.name) candidates.push(`${region.name}, ${country.name}`);
		if (country?.name) candidates.push(country.name);

		for (const name of candidates) {
			try {
				const descRes = await fetch(
					`${endpoint}/api/generate/desc/?name=${encodeURIComponent(name)}`,
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
						break;
					}
				} else {
					console.debug('No description available for', name);
				}
			} catch (e) {
				console.debug('Failed to fetch description for', name, e);
			}
		}
	} catch (e) {
		console.debug('Description generation attempt failed', e);
	}

	res = await fetch(`${endpoint}/api/regions/${region.id}/cities/visits/`, {
		method: 'GET',
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	if (!res.ok) {
		console.error('Failed to fetch visited regions');
		return { status: 500 };
	} else {
		visitedCities = (await res.json()) as VisitedCity[];
	}

	return {
		props: {
			cities,
			region,
			visitedCities,
			description
		}
	};
}) satisfies PageServerLoad;
