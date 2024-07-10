import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { PUBLIC_SERVER_URL } from '$env/static/public';

export const load = (async (event) => {
	const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
	if (!event.locals.user || !event.cookies.get('auth')) {
		return redirect(302, '/login');
	} else {
		let res = await event.fetch(`${endpoint}/api/trips/`, {
			headers: {
				Cookies: event.cookies.get('auth') || ''
			}
		});
		if (res.ok) {
			let data = await res.json();
			return {
				props: {
					trips: data
				}
			};
		} else {
			return {
				status: res.status,
				error: new Error('Failed to fetch data')
			};
		}
	}
	return {};
}) satisfies PageServerLoad;
