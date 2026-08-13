import { fail, redirect } from '@sveltejs/kit';

import type { Actions, PageServerLoad } from './$types';
import { getRandomBackground, getRandomQuote } from '$lib';
import {
	csrfFail,
	djangoBrowserFetch,
	fetchPasswordPolicy,
	fetchSignupLegalLinks,
	getServerEndpoint,
	isPasswordLongEnough,
	mapSignupError,
	requireCsrf,
	setSessionFromResponse,
	signupLegalRequired
} from '$lib/index.server';
import { hasPendingAllauthFlow } from '$lib/server/allauth-flows';
import { getInviteKeyFromUrl, prepareInviteSignup } from '$lib/server/invite-signup';

export const load: PageServerLoad = async (event) => {
	if (event.locals.user) {
		return redirect(302, '/');
	}

	const serverEndpoint = getServerEndpoint();
	const inviteKey = getInviteKeyFromUrl(event.url);
	const inviteSignup = inviteKey ? await prepareInviteSignup(event, inviteKey) : null;

	const [isDisabledFetch, passwordPolicy, signupLegalLinks] = await Promise.all([
		event.fetch(`${serverEndpoint}/auth/is-registration-disabled/`),
		fetchPasswordPolicy(event.fetch, serverEndpoint),
		fetchSignupLegalLinks(event.fetch, serverEndpoint)
	]);
	const isDisabledJson = await isDisabledFetch.json();
	const quote = getRandomQuote();
	const background = getRandomBackground();
	const inviteAllowsSignup = inviteSignup?.valid === true;

	return {
		props: {
			is_disabled: inviteAllowsSignup ? false : isDisabledJson.is_disabled,
			is_disabled_message: isDisabledJson.message,
			invite_key: inviteKey || null,
			inviteSignup,
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
		const inviteKey = (
			formData.get('invite_key')?.toString() ||
			getInviteKeyFromUrl(event.url) ||
			''
		).trim();

		let username = formUsername?.toString().toLocaleLowerCase();

		const serverEndpoint = getServerEndpoint();
		const passwordPolicy = await fetchPasswordPolicy(event.fetch, serverEndpoint);
		const signupLegalLinks = await fetchSignupLegalLinks(event.fetch, serverEndpoint);

		let csrfToken: string;
		try {
			csrfToken = await requireCsrf();
		} catch {
			event.locals.user = null;
			return csrfFail();
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

		if (inviteKey) {
			const inviteState = await prepareInviteSignup(event, inviteKey);
			if (!inviteState.valid) {
				return fail(400, { message: 'auth.invite_invalid_desc' });
			}
		}

		const signupFetch = await djangoBrowserFetch(event, '/auth/browser/v1/auth/signup', {
			method: 'POST',
			csrfToken,
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				username,
				password: password1,
				email,
				first_name,
				last_name,
				accept_terms: acceptTerms,
				...(inviteKey ? { invite_key: inviteKey } : {})
			})
		});
		const signupResponse = await signupFetch.json();

		if (!signupFetch.ok) {
			if (signupFetch.status === 401 && hasPendingAllauthFlow(signupResponse, 'verify_email')) {
				return {
					message: 'auth.user_email_verification_required',
					email_verification_required: true
				};
			}

			return fail(signupFetch.status, mapSignupError(signupResponse, passwordPolicy));
		}

		setSessionFromResponse(event, signupFetch);
		redirect(302, '/');
	}
};
