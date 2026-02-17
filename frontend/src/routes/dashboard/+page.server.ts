import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location, Transportation, Lodging } from '$lib/types';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let adventures: Location[] = [];
		let transportations: Transportation[] = [];
		let lodgings: Lodging[] = [];

		const headers = {
			Cookie: `sessionid=${event.cookies.get('sessionid')}`
		};

		// Fetch all data in parallel
		const [locationsRes, transportationsRes, lodgingsRes, statsRes] = await Promise.all([
			event.fetch(`${serverEndpoint}/api/locations/`, { headers, credentials: 'include' }),
			event.fetch(`${serverEndpoint}/api/transportations/`, { headers, credentials: 'include' }),
			event.fetch(`${serverEndpoint}/api/lodging/`, { headers, credentials: 'include' }),
			event.fetch(`${serverEndpoint}/api/stats/counts/${event.locals.user.username}/`, { headers })
		]);

		let stats = null;
		if (!statsRes.ok) {
			console.error('Failed to fetch user stats');
		} else {
			stats = await statsRes.json();
		}

		if (!locationsRes.ok) {
			let error_message = await locationsRes.json();
			console.error(error_message);
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await locationsRes.json();
			let visited = res.results as Location[];
			// only get the first 3 adventures or less if there are less than 3
			adventures = visited.slice(0, 3);
		}

		if (transportationsRes.ok) {
			const transportationsData = await transportationsRes.json();
			// Handle both paginated and non-paginated responses
			const transportationsList = transportationsData.results || transportationsData;
			transportations = transportationsList.slice(0, 3);
		}

		if (lodgingsRes.ok) {
			const lodgingsData = await lodgingsRes.json();
			// Handle both paginated and non-paginated responses
			const lodgingsList = lodgingsData.results || lodgingsData;
			lodgings = lodgingsList.slice(0, 3);
		}

		return {
			props: {
				adventures,
				transportations,
				lodgings,
				stats
			}
		};
	}
}) satisfies PageServerLoad;
