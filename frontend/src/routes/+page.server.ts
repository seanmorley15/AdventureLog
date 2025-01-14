const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import { redirect, type Actions } from '@sveltejs/kit';
import { themes } from '$lib';
import { fetchCSRFToken } from '$lib/index.server';
import type { PageServerLoad } from './$types';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (event.locals.user) {
		return redirect(302, '/dashboard');
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	setTheme: async ({ url, cookies }) => {
		const theme = url.searchParams.get('theme');
		// change the theme only if it is one of the allowed themes
		if (theme && themes.find((t) => t.name === theme)) {
			cookies.set('colortheme', theme, {
				path: '/',
				maxAge: 60 * 60 * 24 * 365, // 1 year
				sameSite: 'lax'
			});
		}
	},
	logout: async (event) => {
		let sessionId = event.cookies.get('sessionid');
		let csrfToken = await fetchCSRFToken();

		if (!sessionId) {
			return;
		}

		const res = await fetch(`${serverEndpoint}/_allauth/browser/v1/auth/session`, {
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken, // Ensure CSRF token is in header
				Referer: event.url.origin, // Include Referer header
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`
			},
			credentials: 'include'
		});

		// Determine the proper cookie domain
		const hostname = event.url.hostname;
		const domainParts = hostname.split('.');
		const isIPAddress = /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname);
		let cookieDomain: string | undefined = undefined;

		if (!isIPAddress) {
			// Handle domain names
			if (domainParts.length > 2) {
				// For subdomains like app.mydomain.com -> .mydomain.com
				cookieDomain = '.' + domainParts.slice(-2).join('.');
			} else if (domainParts.length === 2) {
				// For root domains like mydomain.com -> .mydomain.com
				cookieDomain = '.' + hostname;
			}
		}
		// No domain is set for IP addresses or single-part hostnames like "localhost"

		// Delete the session cookie
		event.cookies.delete('sessionid', {
			path: '/',
			secure: event.url.protocol === 'https:',
			domain: cookieDomain // Undefined for IP addresses, used for domain names
		});

		if (res.status === 401) {
			return redirect(302, '/login');
		} else {
			return redirect(302, '/');
		}
	},
	setLocale: async ({ url, cookies }) => {
		const locale = url.searchParams.get('locale');
		// change the locale only if it is one of the allowed locales
		if (locale) {
			cookies.set('locale', locale, {
				path: '/',
				maxAge: 60 * 60 * 24 * 365 // 1 year
			});
		}
	}
};
