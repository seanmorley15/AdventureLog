import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location, Collection, SlimCollection } from '$lib/types';

import type { Actions } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';
import { checkLink } from '$lib';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}

	const sessionId = event.cookies.get('sessionid');
	if (!sessionId) {
		return redirect(302, '/login');
	}

	// Get sorting parameters from URL
	const order_by = event.url.searchParams.get('order_by') || 'updated_at';
	const order_direction = event.url.searchParams.get('order_direction') || 'desc';
	const page = event.url.searchParams.get('page') || '1';
	const currentPage = parseInt(page);

	// Common headers for all requests
	const headers = {
		Cookie: `sessionid=${sessionId}`
	};

	// Build API URL with nested=true for lighter payload
	const apiUrl = `${serverEndpoint}/api/collections/?order_by=${order_by}&order_direction=${order_direction}&page=${page}&nested=true`;

	try {
		// Execute all API calls in parallel
		const [collectionsRes, sharedRes, archivedRes, invitesRes] = await Promise.all([
			fetch(apiUrl, { headers, credentials: 'include' }),
			fetch(`${serverEndpoint}/api/collections/shared/?nested=true`, { headers }),
			fetch(`${serverEndpoint}/api/collections/archived/?nested=true`, { headers }),
			fetch(`${serverEndpoint}/api/collections/invites/`, { headers })
		]);

		// Check if main collections request failed (most critical)
		if (!collectionsRes.ok) {
			console.error('Failed to fetch collections:', collectionsRes.status);
			return redirect(302, '/login');
		}

		// Parse responses in parallel
		const [collectionsData, sharedData, archivedData, invitesData] = await Promise.all([
			collectionsRes.json(),
			sharedRes.ok ? sharedRes.json() : [],
			archivedRes.ok ? archivedRes.json() : [],
			invitesRes.ok ? invitesRes.json() : []
		]);

		return {
			props: {
				adventures: collectionsData.results as Location[],
				next: collectionsData.next,
				previous: collectionsData.previous,
				count: collectionsData.count,
				sharedCollections: sharedData as SlimCollection[],
				currentPage,
				order_by,
				order_direction,
				archivedCollections: archivedData as SlimCollection[],
				invites: invitesData
			}
		};
	} catch (error) {
		console.error('Error fetching data:', error);
		return redirect(302, '/login');
	}
}) satisfies PageServerLoad;
