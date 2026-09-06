import type { Cookies, RequestEvent } from '@sveltejs/kit';
// @ts-ignore — psl has no bundled types in this project
import psl from 'psl';

export type SessionCookieOptions = {
	path: '/';
	httpOnly: true;
	sameSite: 'lax';
	secure: boolean;
	domain?: string;
	expires?: Date;
};

/** Parent domain for session cookies on multi-label hostnames (e.g. `.example.com`). */
export function resolveSessionCookieDomain(hostname: string): string | undefined {
	const isIPAddress = /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname);
	const isLocalhost = hostname === 'localhost';
	const isSingleLabel = hostname.split('.').length === 1;

	if (isIPAddress || isLocalhost || isSingleLabel) {
		return undefined;
	}

	const parsed = psl.parse(hostname);
	if (parsed && 'domain' in parsed && parsed.domain) {
		return `.${parsed.domain}`;
	}

	return undefined;
}

export function getSessionCookieOptions(event: Pick<RequestEvent, 'url'>): SessionCookieOptions {
	return {
		path: '/',
		httpOnly: true,
		sameSite: 'lax',
		secure: event.url.protocol === 'https:',
		domain: resolveSessionCookieDomain(event.url.hostname)
	};
}

function getSetCookieHeaders(response: Response): string[] {
	if ('getSetCookie' in response.headers && typeof response.headers.getSetCookie === 'function') {
		return response.headers.getSetCookie();
	}

	const raw = response.headers.get('Set-Cookie');
	if (!raw) {
		return [];
	}

	return raw.split(/,\s*(?=\w+=)/);
}

/** Extract sessionid value from Set-Cookie headers on a Django response. */
export function extractSessionIdFromResponse(response: Response): string | null {
	const setCookieHeaders = getSetCookieHeaders(response);
	const sessionCookie = setCookieHeaders.find((cookie) => cookie.startsWith('sessionid='));
	if (!sessionCookie) {
		return null;
	}

	const sessionIdMatch = sessionCookie.match(/sessionid=([^;]+)/);
	return sessionIdMatch ? sessionIdMatch[1] : null;
}

/** Apply sessionid from a Django Set-Cookie response onto the SvelteKit cookie jar. */
export function setSessionFromResponse(
	event: Pick<RequestEvent, 'cookies' | 'url'>,
	response: Response
): boolean {
	const setCookieHeaders = getSetCookieHeaders(response);
	const sessionCookie = setCookieHeaders.find((cookie) => cookie.startsWith('sessionid='));
	if (!sessionCookie) {
		return false;
	}

	const sessionIdMatch = sessionCookie.match(/sessionid=([^;]+)/);
	if (!sessionIdMatch) {
		return false;
	}

	const expiresMatch = sessionCookie.match(/expires=([^;]+)/i);
	const baseOptions = getSessionCookieOptions(event);

	event.cookies.set('sessionid', sessionIdMatch[1], {
		...baseOptions,
		...(expiresMatch ? { expires: new Date(expiresMatch[1]) } : {})
	});

	return true;
}

/** Remove sessionid using the same domain/path options as set. */
export function clearSessionCookie(event: Pick<RequestEvent, 'cookies' | 'url'>): void {
	const options = getSessionCookieOptions(event);
	event.cookies.delete('sessionid', options);
}

/** Build Cookie header value for csrftoken + optional sessionid. */
export function buildAuthCookieHeader(csrfToken: string, sessionId?: string | null): string {
	const parts = [`csrftoken=${csrfToken}`];
	if (sessionId) {
		parts.push(`sessionid=${sessionId}`);
	}
	return parts.join('; ');
}
