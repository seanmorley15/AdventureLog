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
		let adventures = (await visitedFetch.json()) as Adventure[];

		if (!visitedRegionsFetch.ok) {
			console.error('Failed to fetch visited regions');
			return redirect(302, '/login');
		} else if (!visitedFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			return {
				props: {
					visitedRegions,
					adventures
				}
			};
		}
	}
}) satisfies PageServerLoad;
