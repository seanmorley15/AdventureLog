import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let plannedFetch = await fetch(`${endpoint}/api/adventures/planned/`, {
			headers: {
				Cookie: `${event.cookies.get('auth')}`
			}
		});
		if (!plannedFetch.ok) {
			console.error('Failed to fetch planned adventures');
			return redirect(302, '/login');
		} else {
			let planned = (await plannedFetch.json()) as Adventure[];
			return {
				props: {
					planned
				}
			};
		}
	}
}) satisfies PageServerLoad;
