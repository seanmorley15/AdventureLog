import { fail, redirect, type RequestEvent } from '@sveltejs/kit';
// @ts-ignore
import psl from 'psl';
import type { Actions, PageServerLoad, RouteParams } from './$types';
import { getRandomBackground, getRandomQuote } from '$lib';
import { fetchCSRFToken } from '$lib/index.server';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load: PageServerLoad = async (event) => {
	if (event.locals.user) {
		return redirect(302, '/');
	} else {
		const quote = getRandomQuote();
		const background = getRandomBackground();

		let socialProviderFetch = await event.fetch(`${serverEndpoint}/auth/social-providers/`);
		if (!socialProviderFetch.ok) {
			return fail(500, { message: 'settings.social_providers_error' });
		}
		let socialProviders = await socialProviderFetch.json();

		return {
			props: {
				quote,
				background,
				socialProviders
			}
		};
	}
};

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const formUsername = formData.get('username');
		const username = formUsername?.toString().toLowerCase();
		const password = formData.get('password');
		const totp = formData.get('totp');

		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
		const csrfToken = await fetchCSRFToken();

		// Initial login attempt
		const loginFetch = await event.fetch(`${serverEndpoint}/auth/browser/v1/auth/login`, {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken,
				'Content-Type': 'application/json',
				Cookie: `csrftoken=${csrfToken}`,
				Referer: event.url.origin // Include Referer header
			},
			body: JSON.stringify({ username, password }),
			credentials: 'include'
		});

		if (loginFetch.status === 200) {
			// Login successful without MFA
			handleSuccessfulLogin(event, loginFetch);
			return redirect(302, '/');
		} else if (loginFetch.status === 401) {
			// MFA required
			if (!totp) {
				return fail(401, {
					message: 'settings.mfa_required',
					mfa_required: true
				});
			} else {
				// Attempt MFA authentication
				const sessionId = extractSessionId(loginFetch.headers.get('Set-Cookie'));
				const mfaLoginFetch = await event.fetch(
					`${serverEndpoint}/auth/browser/v1/auth/2fa/authenticate`,
					{
						method: 'POST',
						headers: {
							'X-CSRFToken': csrfToken,
							'Content-Type': 'application/json',
							Cookie: `csrftoken=${csrfToken}; sessionid=${sessionId}`,
							Referer: event.url.origin // Include Referer header
						},
						body: JSON.stringify({ code: totp }),
						credentials: 'include'
					}
				);

				if (mfaLoginFetch.ok) {
					// MFA successful
					handleSuccessfulLogin(event, mfaLoginFetch);
					return redirect(302, '/');
				} else {
					// MFA failed
					const mfaLoginResponse = await mfaLoginFetch.json();
					return fail(401, {
						message: mfaLoginResponse.error || 'settings.invalid_code',
						mfa_required: true
					});
				}
			}
		} else {
			// Login failed
			const loginResponse = await loginFetch.json();
			const firstKey = Object.keys(loginResponse)[0] || 'error';
			const error = loginResponse[firstKey][0] || 'settings.invalid_credentials';
			return fail(400, { message: error });
		}
	}
};

function handleSuccessfulLogin(event: RequestEvent<RouteParams, '/login'>, response: Response) {
	const setCookieHeader = response.headers.get('Set-Cookie');
	if (setCookieHeader) {
		const sessionIdRegex = /sessionid=([^;]+).*?expires=([^;]+)/;
		const match = setCookieHeader.match(sessionIdRegex);
		if (match) {
			const [, sessionId, expiryString] = match;

			// Get the proper cookie domain using psl
			const hostname = event.url.hostname;
			let cookieDomain;

			// Check if hostname is an IP address
			const isIPAddress = /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname);
			const isLocalhost = hostname === 'localhost';
			const isSingleLabel = hostname.split('.').length === 1;

			if (!isIPAddress && !isSingleLabel && !isLocalhost) {
				const parsed = psl.parse(hostname);

				if (parsed && parsed.domain) {
					// Use the parsed domain (e.g., mydomain.com)
					cookieDomain = `.${parsed.domain}`;
				}
			}
			// Do not set a domain for IP addresses or invalid hostnames

			event.cookies.set('sessionid', sessionId, {
				path: '/',
				httpOnly: true,
				sameSite: 'lax',
				secure: event.url.protocol === 'https:',
				expires: new Date(expiryString),
				domain: cookieDomain // Set the domain dynamically or omit if undefined
			});
		}
	}
}

function extractSessionId(setCookieHeader: string | null) {
	if (setCookieHeader) {
		const sessionIdRegex = /sessionid=([^;]+)/;
		const match = setCookieHeader.match(sessionIdRegex);
		return match ? match[1] : '';
	}
	return '';
}
