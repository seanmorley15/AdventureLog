const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Country, Region, VisitedRegion } from '#lib/types.js';
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

	const get = (path: string) =>
		fetch(`${endpoint}${path}`, {
			method: 'GET',
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		});

	// A short description (Wikipedia/Wikidata generated) for the country. Never throws: a country
	// without one is shown without it.
	const fetchDescription = async (name: string): Promise<string | null> => {
		try {
			const descRes = await get(`/api/places/description/?name=${encodeURIComponent(name)}`);
			if (descRes.ok) {
				const descJson = await descRes.json();
				if (descJson && typeof descJson.extract === 'string') {
					return descJson.extract;
				}
			} else {
				console.debug('No description available for', name);
			}
		} catch (e) {
			console.debug('Failed to fetch description:', e);
		}
		return null;
	};

	// The country's regions, the user's visited regions and the country itself do not depend on
	// each other, so ask for all three at once. The description needs the country's name, so it
	// starts the moment the country arrives instead of after everything else.
	const regionsRes = get(`/api/countries/${id}/regions/`);
	const visitedRes = get(`/api/visited-regions/?country=${id}`);
	const countryRes = get(`/api/countries/${id}/`).then(async (response) => ({
		response,
		data: response.ok ? ((await response.json()) as Country) : null
	}));
	const descriptionRes = countryRes.then(({ data }) => (data ? fetchDescription(data.name) : null));

	// We may return early (a 404, a failed request) while the others are still in flight. Their
	// failures are then of no interest, and an unhandled rejection would take the server down.
	for (const pending of [regionsRes, visitedRes, countryRes, descriptionRes]) {
		pending.catch(() => {});
	}

	const regionsResponse = await regionsRes;
	if (!regionsResponse.ok) {
		console.error('Failed to fetch regions');
		return redirect(302, '/404');
	}
	regions = (await regionsResponse.json()) as Region[];

	const visitedResponse = await visitedRes;
	if (!visitedResponse.ok) {
		console.error('Failed to fetch visited regions');
		return { status: 500 };
	}
	visitedRegions = (await visitedResponse.json()) as VisitedRegion[];

	const { response: countryResponse, data: countryData } = await countryRes;
	if (!countryResponse.ok || !countryData) {
		console.error('Failed to fetch country');
		return { status: 500 };
	}
	country = countryData;

	const description = await descriptionRes;

	return {
		props: {
			regions,
			visitedRegions,
			country,
			description
		}
	};
}) satisfies PageServerLoad;
