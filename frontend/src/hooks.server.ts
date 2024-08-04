import type { Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import { fetchCSRFToken, tryRefreshToken } from '$lib/index.server';

export const authHook: Handle = async ({ event, resolve }) => {
	try {
		let authCookie = event.cookies.get('auth');
		let refreshCookie = event.cookies.get('refresh');

		if (!authCookie && !refreshCookie) {
			event.locals.user = null;
			return await resolve(event);
		}

		if (!authCookie && refreshCookie) {
			event.locals.user = null;
			const token = await tryRefreshToken(event.cookies.get('refresh') || '');
			if (token) {
				authCookie = token;
				event.cookies.set('auth', authCookie, {
					httpOnly: true,
					sameSite: 'lax',
					expires: new Date(Date.now() + 60 * 60 * 1000), // 60 minutes
					path: '/'
				});
			} else {
				return await resolve(event);
			}
		}

		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

		let userFetch = await event.fetch(`${serverEndpoint}/auth/user/`, {
			headers: {
				Cookie: `${authCookie}`
			}
		});

		if (!userFetch.ok) {
			console.log('Refreshing token');
			const refreshCookie = event.cookies.get('refresh');

			if (refreshCookie) {
				const csrfToken = await fetchCSRFToken();
				if (!csrfToken) {
					console.error('Failed to fetch CSRF token');
					event.locals.user = null;
					return await resolve(event);
				}

				const refreshFetch = await event.fetch(`${serverEndpoint}/auth/token/refresh/`, {
					method: 'POST',
					headers: {
						'X-CSRFToken': csrfToken,
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({ refresh: refreshCookie })
				});

				if (refreshFetch.ok) {
					const refresh = await refreshFetch.json();
					event.cookies.set('auth', 'auth=' + refresh.access, {
						httpOnly: true,
						sameSite: 'lax',
						expires: new Date(Date.now() + 60 * 60 * 1000), // 60 minutes
						path: '/'
					});

					userFetch = await event.fetch(`${serverEndpoint}/auth/user/`, {
						headers: {
							'X-CSRFToken': csrfToken,
							Cookie: `auth=${refresh.access}`
						}
					});
				}
			}
		}

		if (userFetch.ok) {
			const user = await userFetch.json();
			event.locals.user = user;
		} else {
			event.locals.user = null;
			event.cookies.delete('auth', { path: '/' });
			event.cookies.delete('refresh', { path: '/' });
		}
	} catch (error) {
		console.error('Error in authHook:', error);
		event.locals.user = null;
		event.cookies.delete('auth', { path: '/' });
		event.cookies.delete('refresh', { path: '/' });
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

export const handle = sequence(authHook, themeHook);
