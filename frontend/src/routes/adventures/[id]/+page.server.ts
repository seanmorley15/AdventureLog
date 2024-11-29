import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure, Collection } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/adventures/${id.id}/`, {
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
			}
		};
	} else {
		let adventure = (await request.json()) as Adventure;
		let collection: Collection | null = null;

		if (adventure.collection) {
			let res2 = await fetch(`${endpoint}/api/collections/${adventure.collection}/`, {
				headers: {
					Cookie: `sessionid=${event.cookies.get('sessionid')}`
				},
				credentials: 'include'
			});
			collection = await res2.json();
		}

		return {
			props: {
				adventure,
				collection
			}
		};
	}
}) satisfies PageServerLoad;

import { redirect, type Actions } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

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

		let res = await fetch(`${serverEndpoint}/api/adventures/${event.params.id}`, {
			method: 'DELETE',
			headers: {
				Cookie: `sessionid=${event.cookies.get('sessionid')}; csrftoken=${csrfToken}`,
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
