import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let res = await fetch(`${serverEndpoint}/api/collections/shared/`, {
			headers: {
				Cookie: `${event.cookies.get('auth')}`
			}
		});
		if (!res.ok) {
			return redirect(302, '/login');
		} else {
			return {
				props: {
					collections: await res.json()
				}
			};
		}
	}
}) satisfies PageServerLoad;
