import type { Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

export const authHook: Handle = async ({ event, resolve }) => {
	try {
		let sessionid = event.cookies.get('sessionid');
		console.log('sessionid:', sessionid);

		if (!sessionid) {
			console.log('No sessionid cookie');
			event.locals.user = null;
			return await resolve(event);
		}

		// print all cookies in the request
		console.log('Cookies:', event.request.headers.get('cookie'));

		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

		const cookie = event.request.headers.get('cookie') || '';

		let userFetch = await event.fetch(`${serverEndpoint}/auth/user-metadata/`, {
			headers: {
				cookie
			}
		});

		if (!userFetch.ok) {
			event.locals.user = null;
			event.cookies.delete('sessionid', { path: '/' });
			return await resolve(event);
		}

		if (userFetch.ok) {
			const user = await userFetch.json();
			event.locals.user = user;
			const setCookieHeader = userFetch.headers.get('Set-Cookie');

			console.log('setCookieHeader:', setCookieHeader);

			if (setCookieHeader) {
				// Regular expression to match sessionid cookie and its expiry
				const sessionIdRegex = /sessionid=([^;]+).*?expires=([^;]+)/;
				const match = setCookieHeader.match(sessionIdRegex);

				if (match) {
					const sessionId = match[1];
					const expiryString = match[2];
					const expiryDate = new Date(expiryString);

					console.log('Session ID:', sessionId);
					console.log('Expiry Date:', expiryDate);

					// Set the sessionid cookie
					event.cookies.set('sessionid', sessionId, {
						path: '/',
						httpOnly: true,
						sameSite: 'lax',
						secure: true,
						expires: expiryDate
					});
				}
			}
		} else {
			event.locals.user = null;
			event.cookies.delete('sessionid', { path: '/' });
		}
	} catch (error) {
		console.error('Error in authHook:', error);
		event.locals.user = null;
		event.cookies.delete('sessionid', { path: '/' });
	}

	return await resolve(event);
};

export const themeHook: Handle = async ({ event, resolve }) => {
	let theme = event.url.searchParams.get('theme') || event.cookies.get('colortheme');

	if (theme) {
		return await resolve(event, {
			transformPageChunk: ({ html }) => html.replace('data-theme=""', `data-theme="${theme}"`)
		});
	}

	return await resolve(event);
};

// hook to get the langauge cookie and set the locale
export const i18nHook: Handle = async ({ event, resolve }) => {
	let locale = event.cookies.get('locale');
	if (!locale) {
		return await resolve(event);
	}
	event.locals.locale = locale; // Store the locale in locals
	return await resolve(event);
};

export const handle = sequence(authHook, themeHook, i18nHook);
