import { checkBackendHealth } from '$lib/server/django-proxy';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	const backend = await checkBackendHealth();
	return json(
		{ ok: backend === 'reachable', backend },
		{ status: backend === 'reachable' ? 200 : 503 }
	);
};
