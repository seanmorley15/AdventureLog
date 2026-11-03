import { sequence, type Handle } from '@sveltejs/kit/hooks';
import { themes } from '#lib';
import {
	clearSessionCookie,
	getServerEndpoint,
	setSessionFromResponse
} from '#lib/index.server.js';

const ALLOWED_THEME_NAMES = new Set(themes.map((theme) => theme.name));

/** Routes handled by the Django proxy (`routes/api/[...path]`). */
export function isBackendProxyPath(pathname: string): boolean {
	return pathname.startsWith('/api/');
}

export const authHook: Handle = async ({ event, resolve }) => {
	event.cookies.delete('csrftoken', { path: '/' });
	event.locals.subscription = null;
	event.locals.hasAccess = true;
	event.locals.cloudMode = false;
	event.locals.pendingInviteCount = 0;
	event.locals.unreadCommentCount = 0;

	try {
		if (event.url.pathname.startsWith('/immich/')) {
			return await resolve(event);
		}

		// The /api routes only proxy to Django, which authenticates the session
		// itself. Looking the user up here would add a backend round-trip to every call.
		if (isBackendProxyPath(event.url.pathname)) {
			event.locals.user = null;
			return await resolve(event);
		}

		const sessionid = event.cookies.get('sessionid');

		if (!sessionid) {
			event.locals.user = null;
			return await resolve(event);
		}

		const serverEndpoint = getServerEndpoint();
		const cookie = event.request.headers.get('cookie') || '';

		const userFetch = await event.fetch(`${serverEndpoint}/api/account/`, {
			headers: { cookie }
		});

		if (!userFetch.ok) {
			if (userFetch.status === 429 || userFetch.status >= 500) {
				event.locals.user = null;
				return await resolve(event);
			}

			event.locals.user = null;
			clearSessionCookie(event);
			return await resolve(event);
		}

		const payload = await userFetch.json();
		event.locals.user = payload.user || null;
		event.locals.subscription = payload.subscription || null;
		event.locals.hasAccess = payload.has_access ?? true;
		event.locals.cloudMode = payload.cloud_mode ?? false;
		event.locals.pendingInviteCount = payload.pending_invite_count ?? 0;
		event.locals.unreadCommentCount = payload.unread_comment_count ?? 0;
		setSessionFromResponse(event, userFetch);
	} catch (error) {
		console.error('Error in authHook:', error);
		event.locals.user = null;
		event.locals.subscription = null;
		event.locals.hasAccess = true;
		event.locals.cloudMode = false;
		// Preserve session on transient network errors — do not force logout.
	}

	return await resolve(event);
};

export const themeHook: Handle = async ({ event, resolve }) => {
	const candidate = event.url.searchParams.get('theme') || event.cookies.get('colortheme');
	const theme = candidate && ALLOWED_THEME_NAMES.has(candidate) ? candidate : null;

	if (theme) {
		return await resolve(event, {
			transformPageChunk: ({ html }) => html.replace('data-theme=""', `data-theme="${theme}"`)
		});
	}

	return await resolve(event);
};

export const i18nHook: Handle = async ({ event, resolve }) => {
	let locale = event.cookies.get('locale');
	if (!locale) {
		return await resolve(event);
	}
	event.locals.locale = locale;
	return await resolve(event);
};

export const handle = sequence(authHook, themeHook, i18nHook);
