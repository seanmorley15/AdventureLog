import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { LocationsPage, ProfilePin, ProfileStatsData } from '#lib/components/profile/types.js';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

/** The first page of locations on the profile. Small, so the page paints quickly. */
const FIRST_PAGE_SIZE = 12;

export const load: PageServerLoad = async (event) => {
	const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
	const username = event.params.uuid;
	if (!username) {
		error(404, 'Not found');
	}

	const base = `${endpoint}/api/users/${encodeURIComponent(username)}`;
	const sessionId = event.cookies.get('sessionid');
	const headers: Record<string, string> = { 'Content-Type': 'application/json' };
	if (sessionId) headers['Cookie'] = `sessionid=${sessionId}`;

	/**
	 * A secondary part of the page. It is started now, in parallel with the profile, and
	 * streamed to the page when it is ready; a failure is `null`, never a rejected promise,
	 * so one slow or broken part cannot take the whole profile down.
	 */
	const part = async <T>(path: string): Promise<T | null> => {
		try {
			const res = await event.fetch(`${base}${path}`, { headers });
			if (!res.ok) {
				console.error(`Profile ${path || '/'} failed for ${username}: ${res.status}`);
				return null;
			}
			return (await res.json()) as T;
		} catch (err) {
			console.error(`Profile ${path || '/'} failed for ${username}`, err);
			return null;
		}
	};

	const stats = part<ProfileStatsData>('/stats/');
	const locations = part<LocationsPage>(`/locations/?page_size=${FIRST_PAGE_SIZE}`);
	const pins = part<ProfilePin[]>('/pins/');

	// Only the header and collections are awaited: they decide whether there is a profile.
	let profile;
	try {
		profile = await event.fetch(`${base}/?locations=false`, { headers });
	} catch (err) {
		console.error('Profile fetch failed', err);
		error(503, 'The profile could not be loaded.');
	}
	if (profile.status === 404) {
		error(404, 'Not found');
	}
	if (!profile.ok) {
		error(profile.status >= 500 ? 503 : profile.status, 'The profile could not be loaded.');
	}
	const body = await profile.json();

	return {
		profile: body.user,
		collections: body.collections ?? [],
		// Streamed: each resolves on its own.
		stats,
		locations,
		pins
	};
};
