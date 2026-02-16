import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Pin, VisitedRegion } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export interface LodgingPin {
	id: string;
	name: string;
	latitude: string;
	longitude: string;
	is_visited: boolean;
	type: string;
	is_owned: boolean;
	average_rating: number | null;
	price_tier: number | null;
}

export interface TransportationPin {
	id: string;
	name: string;
	type: string;
	is_visited: boolean;
	is_owned: boolean;
	origin_latitude: string;
	origin_longitude: string;
	destination_latitude: string | null;
	destination_longitude: string | null;
	from_location: string | null;
	to_location: string | null;
	average_rating: number | null;
	price_tier: number | null;
}

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let sessionId = event.cookies.get('sessionid');
		const headers = { Cookie: `sessionid=${sessionId}` };

		// Fetch all pins in parallel
		const [pinFetch, lodgingPinFetch, transportationPinFetch, visitedRegionsFetch] = await Promise.all([
			fetch(`${endpoint}/api/locations/pins/`, { headers }),
			fetch(`${endpoint}/api/lodging/pins/`, { headers }),
			fetch(`${endpoint}/api/transportations/pins/`, { headers }),
			fetch(`${endpoint}/api/visitedregion/`, { headers })
		]);

		if (!visitedRegionsFetch.ok) {
			console.error('Failed to fetch visited regions');
			return redirect(302, '/login');
		}
		if (!pinFetch.ok) {
			console.error('Failed to fetch location pins');
			return redirect(302, '/login');
		}

		let visitedRegions = (await visitedRegionsFetch.json()) as VisitedRegion[];
		let pins = (await pinFetch.json()) as Pin[];
		let lodgingPins: LodgingPin[] = lodgingPinFetch.ok ? await lodgingPinFetch.json() : [];
		let transportationPins: TransportationPin[] = transportationPinFetch.ok ? await transportationPinFetch.json() : [];

		return {
			props: {
				visitedRegions,
				pins,
				lodgingPins,
				transportationPins
			}
		};
	}
}) satisfies PageServerLoad;
