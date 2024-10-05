import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure, VisitedRegion } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let visitedFetch = await fetch(`${endpoint}/api/adventures/all/?include_collections=true`, {
			headers: {
				Cookie: `${event.cookies.get('auth')}`
			}
		});

		let visitedRegionsFetch = await fetch(`${endpoint}/api/visitedregion/`, {
			headers: {
				Cookie: `${event.cookies.get('auth')}`
			}
		});
		let visitedRegions = (await visitedRegionsFetch.json()) as VisitedRegion[];

		if (!visitedFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let visited: Adventure[] = [];
			try {
				let api_result = await visitedFetch.json();
				visited = api_result as Adventure[];
				if (!Array.isArray(visited) || visited.length === 0 || !visited) {
					throw new Error('Visited adventures response is not an array');
				}
			} catch (error) {
				console.error('Error parsing visited adventures:', error);
				return redirect(302, '/login');
			}

			// make a long lat array like this { lngLat: [-20, 0], name: 'Adventure 1' },
			let markers = visited
				.filter((adventure) => adventure.latitude !== null && adventure.longitude !== null)
				.map((adventure) => {
					return {
						lngLat: [adventure.longitude, adventure.latitude],
						name: adventure.name,
						visits: adventure.visits
					};
				});

			console.log('sent');

			return {
				props: {
					markers,
					visitedRegions
				}
			};
		}
	}
}) satisfies PageServerLoad;
