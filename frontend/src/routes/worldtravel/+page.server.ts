const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Country } from '$lib/types';
import { redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { fetchCSRFToken } from '$lib/index.server';

const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		const res = await event.fetch(`${endpoint}/api/countries/`, {
			method: 'GET',
			headers: {
				Cookie: `sessionid=${event.cookies.get('sessionid')}`
			},
			credentials: 'include'
		});
		if (!res.ok) {
			console.error('Failed to fetch countries');
			return { status: 500 };
		} else {
			const countries = (await res.json()) as Country[];
			return {
				props: {
					countries
				}
			};
		}
	}
}) satisfies PageServerLoad;
