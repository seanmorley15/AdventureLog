import { proxyToDjango } from '$lib/server/django-proxy';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = (event) => proxyToDjango(event, 'api');

export const POST: RequestHandler = (event) => proxyToDjango(event, 'api');

export const PATCH: RequestHandler = (event) => proxyToDjango(event, 'api');

export const PUT: RequestHandler = (event) => proxyToDjango(event, 'api');

export const DELETE: RequestHandler = (event) => proxyToDjango(event, 'api');
