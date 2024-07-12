import { fail, redirect } from '@sveltejs/kit';

import type { Actions, PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];

export const load: PageServerLoad = async (event) => {
	if (event.locals.user) {
		return redirect(302, '/');
	}
};

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const formUsername = formData.get('username');
		const formPassword = formData.get('password');

		let username = formUsername?.toString().toLocaleLowerCase();

		const password = formData.get('password');

		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
		const csrfTokenFetch = await event.fetch(`${serverEndpoint}/csrf/`);

		if (!csrfTokenFetch.ok) {
			console.error('Failed to fetch CSRF token');
			event.locals.user = null;
			return fail(500, {
				message: 'Failed to fetch CSRF token'
			});
		}

		const tokenPromise = await csrfTokenFetch.json();
		const csrfToken = tokenPromise.csrfToken;

		const loginFetch = await event.fetch(`${serverEndpoint}/auth/login/`, {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				username,
				password
			})
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
			const token = loginResponse.access;
			const tokenFormatted = `auth=${token}`;
			const refreshToken = `${loginResponse.refresh}`;
			event.cookies.set('auth', tokenFormatted, {
				httpOnly: true,
				sameSite: 'lax',
				expires: new Date(Date.now() + 60 * 60 * 1000), // 60 minutes
				path: '/',
				secure: false
			});
			event.cookies.set('refresh', refreshToken, {
				httpOnly: true,
				sameSite: 'lax',
				expires: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // 1 year
				path: '/',
				secure: false
			});

			return redirect(302, '/');
		}
	}
};
