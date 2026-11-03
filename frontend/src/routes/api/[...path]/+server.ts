import { proxyToDjango } from '#lib/server/django-proxy.js';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = (event) => proxyToDjango(event);

export const POST: RequestHandler = (event) => proxyToDjango(event);

export const PATCH: RequestHandler = (event) => proxyToDjango(event);

export const PUT: RequestHandler = (event) => proxyToDjango(event);

export const DELETE: RequestHandler = (event) => proxyToDjango(event);
