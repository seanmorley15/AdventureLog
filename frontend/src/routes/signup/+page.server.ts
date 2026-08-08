import { error, fail, redirect } from '@sveltejs/kit';

import type { Actions, PageServerLoad } from './$types';
import { getRandomBackground, getRandomQuote } from '$lib';
import {
	fetchPasswordPolicy,
	fetchSignupLegalLinks,
	isPasswordLongEnough,
	mapSignupError,
	signupLegalRequired
} from '$lib/index.server';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load: PageServerLoad = async (event) => {
	if (event.locals.user) {
		return redirect(302, '/');
	}
	let is_disabled_fetch = await event.fetch(`${serverEndpoint}/auth/is-registration-disabled/`);
	let is_disabled_json = await is_disabled_fetch.json();
	let is_disabled = is_disabled_json.is_disabled;
	const passwordPolicy = await fetchPasswordPolicy(event.fetch, serverEndpoint);
	const signupLegalLinks = await fetchSignupLegalLinks(event.fetch, serverEndpoint);
	const quote = getRandomQuote();
	const background = getRandomBackground();

	return {
		props: {
			is_disabled: is_disabled,
			is_disabled_message: is_disabled_json.message,
			passwordPolicy,
			signupLegalLinks,
			quote,
			background
		}
	};
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
		const acceptTerms = formData.get('accept_terms') === 'on';

		let username = formUsername?.toString().toLocaleLowerCase();

		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
		const passwordPolicy = await fetchPasswordPolicy(event.fetch, serverEndpoint);
		const signupLegalLinks = await fetchSignupLegalLinks(event.fetch, serverEndpoint);
		const csrfTokenFetch = await event.fetch(`${serverEndpoint}/csrf/`);

		if (!csrfTokenFetch.ok) {
			event.locals.user = null;
			return fail(500, { message: 'settings.csrf_failed' });
		}

		if (password1 !== password2) {
			return fail(400, { message: 'settings.password_does_not_match' });
		}

		if (!isPasswordLongEnough(password1?.toString(), passwordPolicy)) {
			return fail(400, {
				message: 'auth.password_too_short',
				values: { min: passwordPolicy.min_length }
			});
		}

		if (signupLegalRequired(signupLegalLinks) && !acceptTerms) {
			return fail(400, { message: 'auth.terms_acceptance_required' });
		}

		const tokenPromise = await csrfTokenFetch.json();
		const csrfToken = tokenPromise.csrfToken;

		const loginFetch = await event.fetch(`${serverEndpoint}/auth/browser/v1/auth/signup`, {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken,
				'Content-Type': 'application/json',
				Cookie: `csrftoken=${csrfToken}`,
				Referer: event.url.origin // Include Referer header
			},
			body: JSON.stringify({
				username: username,
				password: password1,
				email: email,
				first_name,
				last_name,
				accept_terms: acceptTerms
			})
		});
		const loginResponse = await loginFetch.json();

		if (!loginFetch.ok) {
			// If backend returns 401, signup succeeded but email verification is required.
			// Return an i18n key (not raw text) so the frontend can show the proper message.
			if (loginFetch.status === 401) {
				return { message: 'auth.user_email_verification_required' };
			}

			return fail(loginFetch.status, mapSignupError(loginResponse, passwordPolicy));
		} else {
			const setCookieHeader = loginFetch.headers.get('Set-Cookie');

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
						secure: event.url.protocol === 'https:',
						expires: expiryDate
					});
				}
			}
			redirect(302, '/');
		}
	}
};
