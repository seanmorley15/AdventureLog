import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location, Pin, VisitedRegion } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let sessionId = event.cookies.get('sessionid');
		const fetchOptions = {
			headers: {
				Cookie: `sessionid=${sessionId}`
			},
			signal: event.request.signal
		};

		let pinFetch = await event.fetch(`${endpoint}/api/locations/pins/`, fetchOptions);

		let visitedRegionsFetch = await event.fetch(`${endpoint}/api/visitedregion/`, fetchOptions);

		let visitedRegions = (await visitedRegionsFetch.json()) as VisitedRegion[];
		let pins = (await pinFetch.json()) as Pin[];

		if (!visitedRegionsFetch.ok) {
			console.error('Failed to fetch visited regions');
			return redirect(302, '/login');
		} else if (!pinFetch.ok) {
			console.error('Failed to fetch location pins');
			return redirect(302, '/login');
		} else {
			return {
				props: {
					visitedRegions,
					pins
				}
			};
		}
	}
}) satisfies PageServerLoad;
