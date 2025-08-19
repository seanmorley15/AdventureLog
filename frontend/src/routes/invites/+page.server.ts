import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { CollectionInvite } from '$lib/types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		redirect(302, '/login');
	}
	let res = await event.fetch(`${serverEndpoint}/api/collections/invites/`, {
		headers: {
			Cookie: `sessionid=${event.cookies.get('sessionid')}`
		},
		credentials: 'include'
	});
	if (!res.ok) {
		return { status: res.status, error: new Error('Failed to fetch invites') };
	}
	const invites = (await res.json()) as CollectionInvite[];
	return { invites };
}) satisfies PageServerLoad;
