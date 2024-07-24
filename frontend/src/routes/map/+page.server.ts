import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure, VisitedRegion } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	let countryCodesToFetch = ['US', 'CA'];
	let geoJSON = {
		type: 'FeatureCollection',
		features: []
	};

	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let visitedFetch = await fetch(`${endpoint}/api/adventures/all/`, {
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

		countryCodesToFetch.forEach(async (code) => {
			let res = await fetch(`${endpoint}/static/data/${code.toLowerCase()}.json`);
			let json = await res.json();
			if (!json) {
				console.error(`Failed to fetch ${code} GeoJSON`);
			} else {
				geoJSON.features = geoJSON.features.concat(json.features);
			}
		});

		if (!visitedFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let visited = (await visitedFetch.json()) as Adventure[];
			console.log('VISITEDL ' + visited);
			// make a long lat array like this { lngLat: [-20, 0], name: 'Adventure 1' },
			let markers = visited
				.filter((adventure) => adventure.latitude !== null && adventure.longitude !== null)
				.map((adventure) => {
					return {
						lngLat: [adventure.longitude, adventure.latitude] as [number, number],
						name: adventure.name,
						type: adventure.type
					};
				});

			return {
				props: {
					markers,
					geoJSON,
					visitedRegions
				}
			};
		}
	}
}) satisfies PageServerLoad;
