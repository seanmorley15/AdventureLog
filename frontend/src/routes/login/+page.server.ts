import { fail, redirect, type RequestEvent } from '@sveltejs/kit';
import type { Actions, PageServerLoad, RouteParams } from './$types';
import { getRandomBackground, getRandomQuote } from '$lib';
import {
	csrfFail,
	djangoBrowserFetch,
	extractSessionIdFromResponse,
	requireCsrf,
	setSessionFromResponse
} from '$lib/index.server';
import { hasPendingAllauthFlow } from '$lib/server/allauth-flows';
import { getServerEndpoint } from '$lib/server/django-proxy';

export const load: PageServerLoad = async (event) => {
	if (event.locals.user) {
		return redirect(302, '/');
	}

	const quote = getRandomQuote();
	const background = getRandomBackground();
	const serverEndpoint = getServerEndpoint();

	let socialProviders: { name: string; url: string; provider: string; usage_required?: boolean }[] =
		[];

	try {
		const socialProviderFetch = await event.fetch(`${serverEndpoint}/auth/social-providers/`);
		if (socialProviderFetch.ok) {
			socialProviders = await socialProviderFetch.json();
		}
	} catch {
		// Degrade gracefully — login still works without social providers.
	}

	const usageRequired = socialProviders.length > 0 ? !!socialProviders[0].usage_required : false;

	if (usageRequired) {
		if (socialProviders.length === 1) {
			return redirect(302, socialProviders[0].url);
		}
		if (socialProviders.length > 1) {
			return {
				props: {
					quote,
					background,
					socialProviders,
					socialOnly: true
				}
			};
		}
	}

	return {
		props: {
			quote,
			background,
			socialProviders
		}
	};
};

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const formUsername = formData.get('username');
		const username = formUsername?.toString().toLowerCase();
		const password = formData.get('password');
		const totp = formData.get('totp');

		let csrfToken: string;
		try {
			csrfToken = await requireCsrf();
		} catch {
			return csrfFail();
		}

		const loginFetch = await djangoBrowserFetch(event, '/auth/browser/v1/auth/login', {
			method: 'POST',
			csrfToken,
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ username, password })
		});

		if (loginFetch.status === 200) {
			setSessionFromResponse(event, loginFetch);
			return redirect(302, resolvePostLoginRedirect(event));
		}

		if (loginFetch.status === 401) {
			const loginResponse = await loginFetch.json();

			if (hasPendingAllauthFlow(loginResponse, 'verify_email')) {
				return fail(401, {
					message: 'auth.user_email_verification_required',
					email_verification_required: true
				});
			}

			if (hasPendingAllauthFlow(loginResponse, 'mfa_authenticate')) {
				if (!totp) {
					return fail(401, {
						message: 'settings.mfa_required',
						mfa_required: true
					});
				}

				const sessionId = extractSessionIdFromResponse(loginFetch);
				if (!sessionId) {
					return fail(401, {
						message: 'settings.invalid_code',
						mfa_required: true
					});
				}

				const mfaLoginFetch = await djangoBrowserFetch(
					event,
					'/auth/browser/v1/auth/2fa/authenticate',
					{
						method: 'POST',
						csrfToken,
						sessionId,
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({ code: totp })
					}
				);

				if (mfaLoginFetch.ok) {
					setSessionFromResponse(event, mfaLoginFetch);
					return redirect(302, resolvePostLoginRedirect(event));
				}

				const mfaLoginResponse = await mfaLoginFetch.json();
				return fail(401, {
					message: mfaLoginResponse.error || 'settings.invalid_code',
					mfa_required: true
				});
			}

			return fail(400, { message: 'auth.login_error' });
		}

		const loginResponse = await loginFetch.json();
		const firstKey = Object.keys(loginResponse)[0] || 'error';
		const error = loginResponse[firstKey][0] || 'settings.invalid_credentials';
		return fail(400, { message: error });
	}
};

function resolvePostLoginRedirect(event: RequestEvent<RouteParams, '/login'>): string {
	const next = event.url.searchParams.get('next');
	if (next && next.startsWith('/') && !next.startsWith('//')) {
		return next;
	}
	return '/';
}
