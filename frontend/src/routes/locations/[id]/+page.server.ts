import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { AdditionalLocation, Location, Collection } from '$lib/types';
import { buildLocationShareMeta } from '$lib/shareMeta.server';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/locations/${id.id}/additional-info/`, {
		headers: {
			Cookie: `sessionid=${event.cookies.get('sessionid')}`
		},
		credentials: 'include'
	});
	if (!request.ok) {
		console.error('Failed to fetch adventure ' + id.id);
		return {
			props: {
				adventure: null
			},
			shareMeta: null
		};
	} else {
		let adventure = (await request.json()) as AdditionalLocation;

		return {
			props: {
				adventure
			},
			shareMeta: buildLocationShareMeta(adventure, event.url.origin)
		};
	}
}) satisfies PageServerLoad;

import { redirect, type Actions } from '@sveltejs/kit';
import { backendApiUrl, fetchCSRFToken } from '$lib/index.server';

export const actions: Actions = {
	delete: async (event) => {
		const id = event.params as { id: string };
		const adventureId = id.id;

		if (!event.locals.user) {
			return redirect(302, '/login');
		}
		if (!adventureId) {
			return {
				status: 400,
				error: new Error('Bad request')
			};
		}

		let csrfToken = await fetchCSRFToken();

		let res = await fetch(backendApiUrl(`/api/locations/${event.params.id}`), {
			method: 'DELETE',
			headers: {
				Referer: event.url.origin, // Include Referer header
				Cookie: `sessionid=${event.cookies.get('sessionid')};
				csrftoken=${csrfToken}`,
				'X-CSRFToken': csrfToken
			},
			credentials: 'include'
		});
		console.log(res);
		if (!res.ok) {
			return {
				status: res.status,
				error: new Error('Failed to delete adventure')
			};
		} else {
			return {
				status: 204
			};
		}
	}
};
