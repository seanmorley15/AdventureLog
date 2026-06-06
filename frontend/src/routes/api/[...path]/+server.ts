import { proxyToDjango } from '$lib/server/django-proxy';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = (event) =>
	proxyToDjango(event, 'api', { requireTrailingSlash: false });

export const POST: RequestHandler = (event) =>
	proxyToDjango(event, 'api', { requireTrailingSlash: true });

export const PATCH: RequestHandler = (event) =>
	proxyToDjango(event, 'api', { requireTrailingSlash: true });

export const PUT: RequestHandler = (event) =>
	proxyToDjango(event, 'api', { requireTrailingSlash: true });

export const DELETE: RequestHandler = (event) =>
	proxyToDjango(event, 'api', { requireTrailingSlash: true });
