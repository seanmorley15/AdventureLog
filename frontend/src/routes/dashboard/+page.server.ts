import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location } from '$lib/types';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let adventures: Location[] = [];

		let initialFetch = await event.fetch(`${serverEndpoint}/api/locations/`, {
			headers: {
				Cookie: `sessionid=${event.cookies.get('sessionid')}`
			},
			credentials: 'include'
		});

		let stats = null;

		let res = await event.fetch(
			`${serverEndpoint}/api/stats/counts/${event.locals.user.username}/`,
			{
				headers: {
					Cookie: `sessionid=${event.cookies.get('sessionid')}`
				}
			}
		);
		if (!res.ok) {
			console.error('Failed to fetch user stats');
		} else {
			stats = await res.json();
		}

		if (!initialFetch.ok) {
			let error_message = await initialFetch.json();
			console.error(error_message);
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let visited = res.results as Location[];
			// only get the first 3 adventures or less if there are less than 3
			adventures = visited.slice(0, 3);
		}

		return {
			props: {
				adventures,
				stats
			}
		};
	}
}) satisfies PageServerLoad;
