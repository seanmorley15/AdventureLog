import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure, Collection } from '$lib/types';

import type { Actions, RequestEvent } from '@sveltejs/kit';
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
		let adventures: Adventure[] = [];
		let sessionId = event.cookies.get('sessionid');
		let initialFetch = await fetch(`${serverEndpoint}/api/collections/?order_by=updated_at`, {
			headers: {
				Cookie: `sessionid=${sessionId}`
			},
			credentials: 'include'
		});
		if (!initialFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let visited = res.results as Adventure[];
			next = res.next;
			previous = res.previous;
			count = res.count;
			adventures = [...adventures, ...visited];
		}

		return {
			props: {
				adventures,
				next,
				previous,
				count
			}
		};
	}
}) satisfies PageServerLoad;
