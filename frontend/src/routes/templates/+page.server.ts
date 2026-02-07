import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}

	const sessionId = event.cookies.get('sessionid');
	if (!sessionId) {
		return redirect(302, '/login');
	}

	const headers = {
		Cookie: `sessionid=${sessionId}`
	};

	try {
		const res = await fetch(`${serverEndpoint}/api/collection-templates/`, {
			headers,
			credentials: 'include'
		});

		if (!res.ok) {
			console.error('Failed to fetch templates:', res.status);
			return {
				props: {
					templates: []
				}
			};
		}

		const templates = await res.json();

		return {
			props: {
				templates: templates.results || templates
			}
		};
	} catch (error) {
		console.error('Error fetching templates:', error);
		return {
			props: {
				templates: []
			}
		};
	}
}) satisfies PageServerLoad;
