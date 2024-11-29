import { fail, redirect } from '@sveltejs/kit';

import type { Actions, PageServerLoad } from './$types';
import { getRandomBackground, getRandomQuote } from '$lib';
import { fetchCSRFToken } from '$lib/index.server';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

export const load: PageServerLoad = async (event) => {
	if (event.locals.user) {
		return redirect(302, '/');
	} else {
		const quote = getRandomQuote();
		const background = getRandomBackground();

		return {
			props: {
				quote,
				background
			}
		};
	}
};

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const formUsername = formData.get('username');

		let username = formUsername?.toString().toLocaleLowerCase();

		const password = formData.get('password');

		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

		const csrfToken = await fetchCSRFToken();

		const loginFetch = await event.fetch(`${serverEndpoint}/_allauth/browser/v1/auth/login`, {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken,
				'Content-Type': 'application/json',
				Cookie: `csrftoken=${csrfToken}`
			},
			body: JSON.stringify({
				username,
				password
			}),
			credentials: 'include'
		});

		const loginResponse = await loginFetch.json();
		if (!loginFetch.ok) {
			// get the value of the first key in the object
			const firstKey = Object.keys(loginResponse)[0] || 'error';
			const error = loginResponse[firstKey][0] || 'Invalid username or password';
			return fail(400, {
				message: error
			});
		} else {
			const setCookieHeader = loginFetch.headers.get('Set-Cookie');

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
			redirect(302, '/');
		}
	}
};
