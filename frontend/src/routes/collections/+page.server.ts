import { fail, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location, Collection, SlimCollection } from '$lib/types';

import type { Actions } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';
import { checkLink } from '$lib';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}

	const sessionId = event.cookies.get('sessionid');
	if (!sessionId) {
		return redirect(302, '/login');
	}

	// Get sorting and filtering parameters from URL
	const order_by = event.url.searchParams.get('order_by') || 'updated_at';
	const order_direction = event.url.searchParams.get('order_direction') || 'desc';
	const status = event.url.searchParams.get('status') || '';
	const page = event.url.searchParams.get('page') || '1';
	const currentPage = parseInt(page);

	// Common headers for all requests
	const headers = {
		Cookie: `sessionid=${sessionId}`
	};

	// Build API URL with nested=true for lighter payload
	const statusParam = status ? `&status=${status}` : '';
	const apiUrl = `${serverEndpoint}/api/collections/?order_by=${order_by}&order_direction=${order_direction}&page=${page}&nested=true${statusParam}`;

	try {
		// Execute all API calls in parallel
		const [collectionsRes, sharedRes, archivedRes, invitesRes] = await Promise.all([
			fetch(apiUrl, { headers, credentials: 'include' }),
			fetch(`${serverEndpoint}/api/collections/shared/?nested=true`, { headers }),
			fetch(`${serverEndpoint}/api/collections/archived/?nested=true`, { headers }),
			fetch(`${serverEndpoint}/api/collections/invites/`, { headers })
		]);

		// Check if main collections request failed (most critical)
		if (!collectionsRes.ok) {
			console.error('Failed to fetch collections:', collectionsRes.status);
			return redirect(302, '/login');
		}

		// Parse responses in parallel
		const [collectionsData, sharedData, archivedData, invitesData] = await Promise.all([
			collectionsRes.json(),
			sharedRes.ok ? sharedRes.json() : [],
			archivedRes.ok ? archivedRes.json() : [],
			invitesRes.ok ? invitesRes.json() : []
		]);

		return {
			props: {
				adventures: collectionsData.results as Location[],
				next: collectionsData.next,
				previous: collectionsData.previous,
				count: collectionsData.count,
				sharedCollections: sharedData as SlimCollection[],
				currentPage,
				order_by,
				order_direction,
				status,
				archivedCollections: archivedData as SlimCollection[],
				invites: invitesData
			}
		};
	} catch (error) {
		console.error('Error fetching data:', error);
		return redirect(302, '/login');
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	restoreData: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		let sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			return redirect(302, '/');
		}
		try {
			const formData = await event.request.formData();
			const file = formData.get('file') as File | null | undefined;

			if (!file || file.size === 0) {
				return fail(400, { message: 'settings.no_file_selected' });
			}

			let csrfToken = await fetchCSRFToken();

			// Create FormData for the API request
			const apiFormData = new FormData();
			apiFormData.append('file', file);

			let res = await fetch(`${serverEndpoint}/api/collections/import/`, {
				method: 'POST',
				headers: {
					Referer: event.url.origin,
					Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
					'X-CSRFToken': csrfToken
				},
				body: apiFormData
			});

			if (!res.ok) {
				const errorData = await res.json();
				return fail(res.status, {
					message: errorData.code
						? `settings.restore_error_${errorData.code}`
						: 'settings.generic_error',
					details: errorData
				});
			}

			return { success: true };
		} catch (error) {
			console.error('Restore error:', error);
			return fail(500, { message: 'settings.generic_error' });
		}
	}
};
