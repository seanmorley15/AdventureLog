import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { ProfilePin, ProfileStatsData } from '#lib/components/profile/types.js';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

/**
 * The map of a profile, for showing inside other websites. It is fetched without the visitor's
 * session, so it shows what a signed-out visitor could see and nothing more, and only for a
 * profile that is public: a profile shared with signed-in users only is not embeddable.
 */
export const load: PageServerLoad = async (event) => {
	const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
	const base = `${endpoint}/api/users/${encodeURIComponent(event.params.username)}`;

	// `?profile=hide` starts with the profile panel folded away; it can still be opened.
	const collapsed = event.url.searchParams.get('profile') === 'hide';

	let profileRes: Response, pinsRes: Response;
	let statsRes: Response;
	try {
		[profileRes, pinsRes, statsRes] = await Promise.all([
			event.fetch(`${base}?locations=false`),
			event.fetch(`${base}/pins`),
			event.fetch(`${base}/stats`)
		]);
	} catch (err) {
		console.error('Embed fetch failed', err);
		error(503, 'The map could not be loaded.');
	}
	if (!profileRes.ok || !pinsRes.ok) {
		error(profileRes.status === 404 || pinsRes.status === 404 ? 404 : 503, 'Unavailable');
	}

	const { user } = await profileRes.json();
	if (user.profile_visibility !== 'public') {
		error(404, 'Unavailable');
	}

	// A map frame is cached briefly by the host's browsers; the pins change rarely.
	event.setHeaders({ 'Cache-Control': 'public, max-age=60' });

	return {
		collapsed,
		profile: {
			username: user.username as string,
			first_name: (user.first_name ?? null) as string | null,
			last_name: (user.last_name ?? null) as string | null,
			profile_pic: (user.profile_pic ?? null) as string | null,
			date_joined: (user.date_joined ?? null) as string | null
		},
		// The panel's numbers are a nicety: without them it still shows who this is.
		stats: (statsRes.ok ? await statsRes.json() : null) as ProfileStatsData | null,
		pins: (await pinsRes.json()) as ProfilePin[]
	};
};
