import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Location, Collection } from '#lib/types.js';
import { buildCollectionShareMeta } from '#lib/shareMeta.server.js';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };

	// A guest link: keep its token in a cookie so later API and media requests carry it,
	// then drop it from the address bar.
	const guestParam = event.url.searchParams.get('guest');
	if (guestParam) {
		event.cookies.set(GUEST_COOKIE, guestParam, {
			path: '/',
			httpOnly: true,
			sameSite: 'lax',
			secure: event.url.protocol === 'https:',
			maxAge: 60 * 60 * 24 * 30
		});
		const clean = new URL(event.url);
		clean.searchParams.delete('guest');
		redirect(303, `${clean.pathname}${clean.search}`);
	}

	let sessionid = event.cookies.get('sessionid');
	const guestToken = event.cookies.get(GUEST_COOKIE);
	const query = new URLSearchParams();
	const secret = event.url.searchParams.get('s');
	if (secret) query.set('s', secret);
	// The owner's preview of what people with the link see.
	if (event.url.searchParams.get('preview') === 'story') query.set('as', 'story');
	const search = query.toString() ? `?${query.toString()}` : '';
	let request = await fetch(`${endpoint}/api/collections/${id.id}/${search}`, {
		headers: {
			Cookie: `sessionid=${sessionid}`,
			...(guestToken ? { 'X-Guest-Token': guestToken } : {})
		}
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
		let collection = (await request.json()) as Collection;

		return {
			props: {
				adventure: collection
			},
			shareMeta: buildCollectionShareMeta(collection, event.url.origin)
		};
	}
}) satisfies PageServerLoad;

import type { Actions } from '@sveltejs/kit';
import { backendApiUrl, fetchCSRFToken } from '#lib/index.server.js';
import { GUEST_COOKIE } from '#lib/server/django-proxy.js';

export const actions: Actions = {
	delete: async (event) => {
		const id = event.params as { id: string };
		const adventureId = id.id;

		if (!adventureId) {
			return {
				status: 400,
				error: new Error('Bad request')
			};
		}

		let sessionId = event.cookies.get('sessionid');

		if (!sessionId) {
			return {
				status: 401,
				error: new Error('Unauthorized')
			};
		}

		let csrfToken = await fetchCSRFToken();

		let res = await fetch(backendApiUrl(`/api/collections/${event.params.id}`), {
			method: 'DELETE',
			headers: {
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken,
				Referer: event.url.origin // Include Referer header
			},
			credentials: 'include'
		});

		if (!res.ok) {
			return {
				status: res.status,
				error: new Error('Failed to delete collection')
			};
		} else {
			return {
				status: 204
			};
		}
	}
};
