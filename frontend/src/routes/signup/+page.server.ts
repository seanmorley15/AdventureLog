import { error, fail, redirect } from '@sveltejs/kit';

import type { Actions, PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load: PageServerLoad = async (event) => {
	if (event.locals.user) {
		return redirect(302, '/');
	}
	let is_disabled = await event.fetch(`${serverEndpoint}/auth/is-registration-disabled/`);
	let is_disabled_json = await is_disabled.json();
	console.log(is_disabled_json);
	if (is_disabled_json.is_disabled) {
		return {
			is_disabled: true
		};
	} else {
		return {
			is_disabled: false
		};
	}
};
export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const formUsername = formData.get('username');
		const password1 = formData.get('password1');
		const password2 = formData.get('password2');
		const email = formData.get('email');
		const first_name = formData.get('first_name');
		const last_name = formData.get('last_name');

		let username = formUsername?.toString().toLocaleLowerCase();

		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
		const csrfTokenFetch = await event.fetch(`${serverEndpoint}/csrf/`);

		if (!csrfTokenFetch.ok) {
			event.locals.user = null;
			return fail(500, { message: 'Failed to fetch CSRF token' });
		}

		const tokenPromise = await csrfTokenFetch.json();
		const csrfToken = tokenPromise.csrfToken;

		const loginFetch = await event.fetch(`${serverEndpoint}/auth/registration/`, {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				username: username,
				password1: password1,
				password2: password2,
				email: email,
				first_name,
				last_name
			})
		});
		const loginResponse = await loginFetch.json();

		if (!loginFetch.ok) {
			// get the value of the first key in the object
			const firstKey = Object.keys(loginResponse)[0] || 'error';
			const error =
				loginResponse[firstKey][0] || 'Failed to register user. Check your inputs and try again.';
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
				path: '/'
			});
			event.cookies.set('refresh', refreshToken, {
				httpOnly: true,
				sameSite: 'lax',
				expires: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // 1 year
				path: '/'
			});

			return redirect(302, '/');
		}
	}
};
