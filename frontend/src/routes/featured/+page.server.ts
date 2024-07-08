import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let visitedFetch = await fetch(`${endpoint}/api/adventures/featured/`, {
			headers: {
				Cookie: `${event.cookies.get('auth')}`
			}
		});
		if (!visitedFetch.ok) {
			console.error('Failed to fetch featured adventures');
			return redirect(302, '/login');
		} else {
			let featured = (await visitedFetch.json()) as Adventure[];
			return {
				props: {
					featured
				}
			};
		}
	}
}) satisfies PageServerLoad;
