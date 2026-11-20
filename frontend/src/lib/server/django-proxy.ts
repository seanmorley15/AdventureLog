import type { RequestEvent } from '@sveltejs/kit';

export function getServerEndpoint(): string {
	return process.env['PUBLIC_SERVER_URL'] || 'http://localhost:8000';
}

// The proxy sends one token as both the csrftoken cookie and the X-CSRFToken header, and
// Django only checks that the two match. There is no server-side state behind it, so one
// token can serve many requests. Fetching a fresh one per request cost a backend call each.
const CSRF_TOKEN_TTL_MS = 10 * 60 * 1000;
let cachedCsrf: { token: string; expires: number } | null = null;
let inflightCsrf: Promise<string | null> | null = null;

async function requestCSRFToken(): Promise<string | null> {
	const csrfTokenFetch = await fetch(`${getServerEndpoint()}/api/auth/csrf/`);
	if (csrfTokenFetch.ok) {
		const csrfToken = await csrfTokenFetch.json();
		return csrfToken.csrf_token ?? null;
	}
	return null;
}

/** A CSRF token for the Django backend, cached for a few minutes. */
// Typed loosely, as before: callers drop it straight into header objects.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetchCSRFToken = async (forceRefresh = false): Promise<any> => {
	const now = Date.now();
	if (!forceRefresh && cachedCsrf && cachedCsrf.expires > now) return cachedCsrf.token;
	if (!inflightCsrf) {
		inflightCsrf = requestCSRFToken()
			.then((token) => {
				cachedCsrf = token ? { token, expires: Date.now() + CSRF_TOKEN_TTL_MS } : null;
				return token;
			})
			.finally(() => {
				inflightCsrf = null;
			});
	}
	return inflightCsrf;
};

/** Cookie holding the token of a collection guest link the visitor opened. */
export const GUEST_COOKIE = 'adventurelog_guest';

/** Allauth headless routes (`/api/auth/browser/v1/...`) have no trailing slash; every other API route does. */
const NO_TRAILING_SLASH_PREFIXES = ['auth/browser/', 'auth/app/'];

/** Routes that are not DRF JSON endpoints, so they must not get `?format=json`. */
const NO_FORMAT_PARAM_PREFIXES = [...NO_TRAILING_SLASH_PREFIXES, 'docs/', 'schema/'];

/** Headers that must not be forwarded to Node fetch (undici rejects hop-by-hop headers). */
const FORBIDDEN_PROXY_HEADERS = new Set([
	'connection',
	'content-length',
	'host',
	'keep-alive',
	'proxy-authenticate',
	'proxy-authorization',
	'te',
	'trailer',
	'transfer-encoding',
	'upgrade'
]);

/** BCP-47-ish tag only: no lists, q-values, or header-injection payloads. */
const LOCALE_RE = /^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/;

function sanitizeProxyRequestHeaders(headers: Headers): Record<string, string> {
	const result: Record<string, string> = {};
	for (const [key, value] of headers) {
		if (!FORBIDDEN_PROXY_HEADERS.has(key.toLowerCase())) {
			result[key] = value;
		}
	}
	return result;
}

/** DRF answers browsers (Accept: text/html) with its HTML page in debug mode; ask for JSON. */
function formatSearchParam(path: string, search: string, method: string): string {
	if (NO_FORMAT_PARAM_PREFIXES.some((prefix) => path.startsWith(prefix))) {
		return search;
	}
	if (method === 'GET' || method === 'PATCH' || method === 'PUT' || method === 'DELETE') {
		return search ? `${search}&format=json` : '?format=json';
	}
	return search;
}

function needsTrailingSlash(path: string): boolean {
	if (NO_TRAILING_SLASH_PREFIXES.some((prefix) => path.startsWith(prefix))) {
		return false;
	}
	return !path.endsWith('/');
}

/** Build a backend API URL with a trailing slash before query params. */
export function backendApiUrl(path: string, search = ''): string {
	const endpoint = getServerEndpoint();
	const normalized = path.startsWith('/') ? path : `/${path}`;
	const [pathname, embeddedSearch = ''] = normalized.split('?');
	const slashPath = pathname.endsWith('/') ? pathname : `${pathname}/`;
	const query = search || embeddedSearch;
	return `${endpoint}${slashPath}${query ? (query.startsWith('?') ? query : `?${query}`) : ''}`;
}

/** Forward a browser request under `/api/` to the same path on Django. */
export async function proxyToDjango(event: RequestEvent) {
	const { url, params, request, fetch, cookies } = event;
	const path = params.path as string;
	let targetUrl = `${getServerEndpoint()}/api/${path}`;
	if (needsTrailingSlash(path)) {
		targetUrl += '/';
	}
	targetUrl += formatSearchParam(path, url.search, request.method);

	const headers = new Headers(request.headers);
	cookies.delete('csrftoken', { path: '/' });
	const proxyHeaders = sanitizeProxyRequestHeaders(headers);
	// Never trust a client-supplied locale header; only the cookie-derived one.
	for (const key of Object.keys(proxyHeaders)) {
		if (key.toLowerCase() === 'x-adventurelog-locale') delete proxyHeaders[key];
	}
	const locale = event.locals.locale;
	if (locale && LOCALE_RE.test(locale)) {
		proxyHeaders['X-AdventureLog-Locale'] = locale;
	}

	let csrfToken = await fetchCSRFToken();
	if (!csrfToken) {
		return Response.json(
			{ detail: 'The server could not be reached for a CSRF token.', code: 'csrf_unavailable' },
			{ status: 502 }
		);
	}

	const sessionId = cookies.get('sessionid');
	// Someone who opened a guest link has no session; the link's token rides along instead.
	const guestToken = cookies.get(GUEST_COOKIE);
	const isUnsafe = request.method !== 'GET' && request.method !== 'HEAD';

	try {
		// Bytes, not text: request.text() UTF-8-decodes and corrupts binary uploads. The request
		// stays buffered (bounded by BODY_SIZE_LIMIT) because a stale CSRF token resends it below,
		// and a stream can only be read once.
		const body = isUnsafe ? await request.arrayBuffer() : undefined;
		const send = (token: string) =>
			fetch(targetUrl, {
				method: request.method,
				headers: {
					...proxyHeaders,
					'X-CSRFToken': token,
					...(guestToken ? { 'X-Guest-Token': guestToken } : {}),
					Cookie: `csrftoken=${token}${sessionId ? `; sessionid=${sessionId}` : ''}`
				},
				body,
				credentials: 'include',
				signal: request.signal
			});

		let response = await send(csrfToken);

		// A cached token the backend no longer accepts (e.g. after a backend restart that
		// changed the secret key): fetch a fresh one and retry once.
		if (isUnsafe && response.status === 403) {
			const detail = await response.clone().text();
			if (detail.includes('CSRF')) {
				const fresh = await fetchCSRFToken(true);
				if (fresh && fresh !== csrfToken) {
					csrfToken = fresh;
					response = await send(fresh);
				}
			}
		}

		if (response.status === 204) {
			return new Response(null, {
				status: 204,
				headers: response.headers
			});
		}

		const cleanHeaders = new Headers(response.headers);
		cleanHeaders.delete('set-cookie');

		// Stream the body through. Buffering it (arrayBuffer) held every export and download in
		// memory, and glibc rarely gives that memory back, so the process stayed large.
		return new Response(response.body, {
			status: response.status,
			headers: cleanHeaders
		});
	} catch (error) {
		if (request.signal.aborted) {
			return new Response(null, { status: 499 });
		}
		console.error('Error forwarding request:', error);
		return Response.json(
			{ detail: 'The server could not be reached.', code: 'backend_unreachable' },
			{ status: 502 }
		);
	}
}

export async function checkBackendHealth(): Promise<'reachable' | 'unreachable'> {
	try {
		const response = await fetch(`${getServerEndpoint()}/health/`, { method: 'GET' });
		return response.ok ? 'reachable' : 'unreachable';
	} catch {
		return 'unreachable';
	}
}
