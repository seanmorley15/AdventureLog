import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure, Collection } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const id = event.params as { id: string };
	let request = await fetch(`${endpoint}/api/adventures/${id.id}/`, {
		headers: {
			Cookie: `${event.cookies.get('auth')}`
		}
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
					Cookie: `${event.cookies.get('auth')}`
				}
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

import type { Actions } from '@sveltejs/kit';
import { tryRefreshToken } from '$lib/index.server';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const actions: Actions = {
	delete: async (event) => {
		const id = event.params as { id: string };
		const adventureId = id.id;

		if (!event.locals.user) {
			const refresh = event.cookies.get('refresh');
			let auth = event.cookies.get('auth');
			if (!refresh) {
				return {
					status: 401,
					body: { message: 'Unauthorized' }
				};
			}
			let res = await tryRefreshToken(refresh);
			if (res) {
				auth = res;
				event.cookies.set('auth', auth, {
					httpOnly: true,
					sameSite: 'lax',
					expires: new Date(Date.now() + 60 * 60 * 1000), // 60 minutes
					path: '/'
				});
			} else {
				return {
					status: 401,
					body: { message: 'Unauthorized' }
				};
			}
		}
		if (!adventureId) {
			return {
				status: 400,
				error: new Error('Bad request')
			};
		}

		let res = await fetch(`${serverEndpoint}/api/adventures/${event.params.id}`, {
			method: 'DELETE',
			headers: {
				Cookie: `${event.cookies.get('auth')}`,
				'Content-Type': 'application/json'
			}
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
