import { fetchCSRFToken } from '$lib/index.server';
import type { PageServerLoad } from './$types';

export const load = (async (event) => {
	// get key from route params
	const key = event.params.key;
	if (!key) {
		return { status: 404 };
	}
	const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
	const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
	const csrfToken = await fetchCSRFToken();

	let verifyFetch = await event.fetch(`${serverEndpoint}/auth/browser/v1/auth/email/verify`, {
		headers: {
			Cookie: `csrftoken=${csrfToken}`,
			'X-CSRFToken': csrfToken
		},
		method: 'POST',
		credentials: 'include',

		body: JSON.stringify({ key: key })
	});
	if (verifyFetch.ok || verifyFetch.status == 401) {
		return {
			verified: true
		};
	} else {
		let error_message = await verifyFetch.json();
		console.error(error_message);
		console.error('Failed to verify email');
		return { status: 404 };
	}
}) satisfies PageServerLoad;
