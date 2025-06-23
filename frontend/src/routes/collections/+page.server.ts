import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure, Collection } from '$lib/types';

import type { Actions } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';
import { checkLink } from '$lib';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let next = null;
		let previous = null;
		let count = 0;
		let collections: Adventure[] = [];
		let sessionId = event.cookies.get('sessionid');

		// Get sorting parameters from URL
		const order_by = event.url.searchParams.get('order_by') || 'updated_at';
		const order_direction = event.url.searchParams.get('order_direction') || 'desc';
		const page = event.url.searchParams.get('page') || '1';

		// Build API URL with parameters
		let apiUrl = `${serverEndpoint}/api/collections/?order_by=${order_by}&order_direction=${order_direction}&page=${page}`;

		let initialFetch = await fetch(apiUrl, {
			headers: {
				Cookie: `sessionid=${sessionId}`
			},
			credentials: 'include'
		});
		if (!initialFetch.ok) {
			console.error('Failed to fetch collections');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let visited = res.results as Adventure[];
			next = res.next;
			previous = res.previous;
			count = res.count;
			collections = [...collections, ...visited];
		}

		let sharedRes = await fetch(`${serverEndpoint}/api/collections/shared/`, {
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		});
		if (!sharedRes.ok) {
			console.error('Failed to fetch shared collections');
			return redirect(302, '/login');
		}
		let sharedCollections = (await sharedRes.json()) as Collection[];

		let archivedRes = await fetch(`${serverEndpoint}/api/collections/archived/`, {
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		});
		if (!archivedRes.ok) {
			console.error('Failed to fetch archived collections');
			return redirect(302, '/login');
		}
		let archivedCollections = (await archivedRes.json()) as Collection[];

		// Calculate current page from URL
		const currentPage = parseInt(page);

		return {
			props: {
				adventures: collections,
				next,
				previous,
				count,
				sharedCollections,
				currentPage,
				order_by,
				order_direction,
				archivedCollections
			}
		};
	}
}) satisfies PageServerLoad;
