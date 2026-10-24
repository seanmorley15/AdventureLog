import { fail } from '@sveltejs/kit';
import type { RequestEvent } from '@sveltejs/kit';
import { fetchCSRFToken, getServerEndpoint } from '$lib/server/django-proxy';
import { buildAuthCookieHeader } from '$lib/server/session-cookies';

export class CsrfError extends Error {
	constructor(message = 'CSRF token is missing or invalid') {
		super(message);
		this.name = 'CsrfError';
	}
}

/** Fetch a CSRF token or throw — use in form actions that must not proceed without one. */
export async function requireCsrf(): Promise<string> {
	const csrfToken = await fetchCSRFToken();
	if (!csrfToken) {
		throw new CsrfError();
	}
	return csrfToken;
}

/** Return a SvelteKit fail response when CSRF cannot be obtained. */
export function csrfFail(status = 500) {
	return fail(status, { message: 'settings.csrf_failed' });
}

/**
 * Session-authenticated fetch to custom Django /auth/* and /api/* endpoints.
 * Does not attach CSRF — use for GET load functions only.
 */
export async function djangoSessionFetch(
	event: Pick<RequestEvent, 'fetch' | 'cookies'>,
	path: string,
	init: RequestInit = {}
): Promise<Response> {
	const sessionId = event.cookies.get('sessionid');
	const endpoint = getServerEndpoint();
	const normalizedPath = path.startsWith('/') ? path : `/${path}`;

	return event.fetch(`${endpoint}${normalizedPath}`, {
		...init,
		headers: {
			...(init.headers ?? {}),
			...(sessionId ? { Cookie: `sessionid=${sessionId}` } : {})
		}
	});
}

/** Parse JSON from a session fetch, returning null when the response is not ok. */
export async function djangoSessionJson<T>(
	event: Pick<RequestEvent, 'fetch' | 'cookies'>,
	path: string,
	init: RequestInit = {}
): Promise<T | null> {
	const response = await djangoSessionFetch(event, path, init);
	if (!response.ok) {
		return null;
	}
	return (await response.json()) as T;
}

type DjangoBrowserFetchInit = Omit<RequestInit, 'headers'> & {
	headers?: Record<string, string>;
	sessionId?: string | null;
	csrfToken?: string;
};

/**
 * Authenticated fetch to django-allauth headless browser endpoints.
 * Always attaches CSRF; includes session cookie when present or overridden.
 */
export async function djangoBrowserFetch(
	event: Pick<RequestEvent, 'fetch' | 'cookies' | 'url'>,
	path: string,
	init: DjangoBrowserFetchInit = {}
): Promise<Response> {
	const csrfToken = init.csrfToken ?? (await requireCsrf());
	const sessionId = init.sessionId ?? event.cookies.get('sessionid');
	const endpoint = getServerEndpoint();
	const normalizedPath = path.startsWith('/') ? path : `/${path}`;

	const { headers: extraHeaders = {}, sessionId: _sessionId, csrfToken: _csrf, ...rest } = init;

	return event.fetch(`${endpoint}${normalizedPath}`, {
		credentials: 'include',
		...rest,
		headers: {
			'X-CSRFToken': csrfToken,
			Cookie: buildAuthCookieHeader(csrfToken, sessionId),
			Referer: event.url.origin,
			...extraHeaders
		}
	});
}
