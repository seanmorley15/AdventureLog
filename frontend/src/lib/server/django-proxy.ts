import { json, type RequestEvent } from '@sveltejs/kit';

export function getServerEndpoint(): string {
	return process.env['PUBLIC_SERVER_URL'] || 'http://localhost:8000';
}

export const fetchCSRFToken = async () => {
	const csrfTokenFetch = await fetch(`${getServerEndpoint()}/csrf/`);
	if (csrfTokenFetch.ok) {
		const csrfToken = await csrfTokenFetch.json();
		return csrfToken.csrfToken;
	}
	return null;
};

type ProxyBasePath = 'api' | 'auth';

type ProxyOptions = {
	requireTrailingSlash?: boolean;
	responseType?: 'text' | 'arrayBuffer';
	shouldRequireTrailingSlash?: (path: string) => boolean;
	formatSearchParam?: (search: string, method: string) => string;
};

const authTrailingSlashPaths = ['disable-password', 'mobile-qr'];
const authTrailingSlashPrefixes = ['api-keys'];

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

function sanitizeProxyRequestHeaders(headers: Headers): Record<string, string> {
	const result: Record<string, string> = {};
	for (const [key, value] of headers) {
		if (!FORBIDDEN_PROXY_HEADERS.has(key.toLowerCase())) {
			result[key] = value;
		}
	}
	return result;
}

function defaultFormatSearchParam(search: string, method: string, basePath: ProxyBasePath): string {
	if (basePath === 'api') {
		if (method === 'GET' || method === 'PATCH' || method === 'PUT' || method === 'DELETE') {
			return search ? `${search}&format=json` : '?format=json';
		}
		return search;
	}
	return search;
}

function authRequiresTrailingSlash(path: string, requireTrailingSlash: boolean): boolean {
	return (
		requireTrailingSlash ||
		authTrailingSlashPaths.includes(path) ||
		authTrailingSlashPrefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))
	);
}

export async function proxyToDjango(
	event: RequestEvent,
	basePath: ProxyBasePath,
	options: ProxyOptions = {}
) {
	const { url, params, request, fetch, cookies } = event;
	const path = params.path as string;
	const endpoint = getServerEndpoint();
	let targetUrl = `${endpoint}/${basePath}/${path}`;

	const requireTrailingSlash =
		basePath === 'auth'
			? authRequiresTrailingSlash(path, options.requireTrailingSlash ?? false)
			: (options.requireTrailingSlash ?? false);

	if (requireTrailingSlash && !targetUrl.endsWith('/')) {
		targetUrl += '/';
	}

	const searchParam =
		options.formatSearchParam?.(url.search, request.method) ??
		defaultFormatSearchParam(url.search, request.method, basePath);
	targetUrl += searchParam;

	const headers = new Headers(request.headers);
	cookies.delete('csrftoken', { path: '/' });

	const csrfToken = await fetchCSRFToken();
	if (!csrfToken) {
		return json({ error: 'CSRF token is missing or invalid' }, { status: 400 });
	}

	const sessionId = cookies.get('sessionid');
	const cookieHeader = `csrftoken=${csrfToken}${sessionId ? `; sessionid=${sessionId}` : ''}`;

	try {
		const response = await fetch(targetUrl, {
			method: request.method,
			headers: {
				...sanitizeProxyRequestHeaders(headers),
				'X-CSRFToken': csrfToken,
				Cookie: cookieHeader
			},
			body:
				request.method !== 'GET' && request.method !== 'HEAD' ? await request.text() : undefined,
			credentials: 'include'
		});

		if (response.status === 204) {
			return new Response(null, {
				status: 204,
				headers: response.headers
			});
		}

		const responseType = options.responseType ?? (basePath === 'api' ? 'arrayBuffer' : 'text');
		const responseData =
			responseType === 'arrayBuffer' ? await response.arrayBuffer() : await response.text();

		const cleanHeaders = new Headers(response.headers);
		cleanHeaders.delete('set-cookie');

		return new Response(responseData, {
			status: response.status,
			headers: cleanHeaders
		});
	} catch (error) {
		console.error('Error forwarding request:', error);
		return json({ error: 'Internal Server Error' }, { status: 500 });
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
