import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let visitedFetch = await fetch(`${endpoint}/api/adventures/`, {
			headers: {
				Cookie: `${event.cookies.get('auth')}`
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
						name: adventure.name
					};
				});
			return {
				props: {
					markers
				}
			};
		}
	}
}) satisfies PageServerLoad;
