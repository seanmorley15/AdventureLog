import { proxyToDjango } from '$lib/server/django-proxy';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = (event) => proxyToDjango(event, 'auth');

export const POST: RequestHandler = (event) => proxyToDjango(event, 'auth');

export const PATCH: RequestHandler = (event) => proxyToDjango(event, 'auth');

export const PUT: RequestHandler = (event) => proxyToDjango(event, 'auth');

export const DELETE: RequestHandler = (event) => proxyToDjango(event, 'auth');
