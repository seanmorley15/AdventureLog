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
	const requestedOrder = event.url.searchParams.get('order_by') || 'updated_at';
	const order_by = ['updated_at', 'name', 'start_date'].includes(requestedOrder)
		? requestedOrder
		: 'updated_at';
	const order_direction = event.url.searchParams.get('order_direction') || 'desc';
	const rawStatus = event.url.searchParams.get('status') || '';
	const rawType = event.url.searchParams.get('type') || '';
	// Older links used status=folder. The list API filters that with type=folder.
	const type = rawStatus === 'folder' ? 'folder' : rawType;
	const status = rawStatus === 'folder' ? '' : rawStatus;
	const page = event.url.searchParams.get('page') || '1';
	const currentPage = parseInt(page);

	// Common headers for all requests
	const headers = {
		Cookie: `sessionid=${sessionId}`
	};

	// The page keeps order_by/order_direction in its own URL; the API takes one `ordering`.
	const ordering = `${order_direction === 'desc' ? '-' : ''}${order_by}`;
	const params = new URLSearchParams({ ordering, page });
	if (status === 'upcoming' || status === 'in_progress' || status === 'completed') {
		params.set('status', status);
	}
	if (type === 'folder' || type === 'trip') {
		params.set('type', type);
	}
	// The shared and archived tabs show everything, as before: one large page.
	const allOf = (extra: Record<string, string>) =>
		new URLSearchParams({ ordering: '-updated_at', page_size: '1000', ...extra });

	try {
		// Execute all API calls in parallel
		const [collectionsRes, sharedRes, archivedRes, invitesRes] = await Promise.all([
			fetch(`${serverEndpoint}/api/collections/?${params}`, { headers, credentials: 'include' }),
			fetch(`${serverEndpoint}/api/collections/?${allOf({ membership: 'shared' })}`, { headers }),
			fetch(`${serverEndpoint}/api/collections/?${allOf({ archived: 'true' })}`, { headers }),
			fetch(`${serverEndpoint}/api/collections/invitations/`, { headers })
		]);

		// Check if main collections request failed (most critical)
		if (!collectionsRes.ok) {
			console.error('Failed to fetch collections:', collectionsRes.status);
			return redirect(302, '/login');
		}

		// Parse responses in parallel
		const [collectionsData, sharedData, archivedData, invitesData] = await Promise.all([
			collectionsRes.json(),
			sharedRes.ok ? sharedRes.json() : { results: [] },
			archivedRes.ok ? archivedRes.json() : { results: [] },
			invitesRes.ok ? invitesRes.json() : []
		]);

		return {
			props: {
				adventures: collectionsData.results as Location[],
				next: collectionsData.next,
				previous: collectionsData.previous,
				count: collectionsData.count,
				sharedCollections: sharedData.results as SlimCollection[],
				currentPage,
				order_by,
				order_direction,
				status,
				type,
				archivedCollections: archivedData.results as SlimCollection[],
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
			// 'link' reuses places the user already has; 'create' makes new copies.
			const existingLocations = formData.get('existing_locations') === 'create' ? 'create' : 'link';
			apiFormData.append('existing_locations', existingLocations);

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
					message: 'settings.restore_error',
					values: { detail: errorData.detail ?? '' },
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
