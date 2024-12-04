import type { Adventure } from '$lib/types';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	let sessionId = event.cookies.get('sessionid');
	let visitedFetch = await fetch(`${endpoint}/api/adventures/all/?include_collections=true`, {
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	let adventures = (await visitedFetch.json()) as Adventure[];

	return {
		props: {
			adventures
		}
	};
}) satisfies PageServerLoad;
