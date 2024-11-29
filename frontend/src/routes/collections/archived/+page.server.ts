import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure } from '$lib/types';
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let sessionId = event.cookies.get('sessionid');
		let adventures: Adventure[] = [];
		let initialFetch = await fetch(`${serverEndpoint}/api/collections/archived/`, {
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		});
		if (!initialFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let visited = res as Adventure[];
			adventures = [...adventures, ...visited];
		}

		return {
			props: {
				adventures
			}
		};
	}
}) satisfies PageServerLoad;
