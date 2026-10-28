import { checkBackendHealth } from '#lib/server/django-proxy.js';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	const backend = await checkBackendHealth();
	return Response.json(
		{ ok: backend === 'reachable', backend },
		{ status: backend === 'reachable' ? 200 : 503 }
	);
};
