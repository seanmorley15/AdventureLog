import { fail, redirect } from '@sveltejs/kit';
import {
	csrfFail,
	djangoBrowserFetch,
	fetchPasswordPolicy,
	isPasswordLongEnough,
	isPasswordResetSuccess,
	mapAllauthPasswordError,
	requireCsrf
} from '$lib/index.server';
import type { PageServerLoad, Actions } from './$types';
import { getServerEndpoint } from '$lib/server/django-proxy';

export const load = (async ({ params, fetch }) => {
	const key = params.key;
	if (!key) {
		throw redirect(302, '/');
	}
	const passwordPolicy = await fetchPasswordPolicy(fetch, getServerEndpoint());
	return { key, passwordPolicy };
}) satisfies PageServerLoad;

export const actions: Actions = {
	default: async (event) => {
		const formData = await event.request.formData();
		const password = formData.get('password');
		const confirm_password = formData.get('confirm_password');
		const key = event.params.key;

		if (!password || !confirm_password) {
			return fail(400, { message: 'auth.both_passwords_required' });
		}

		if (password !== confirm_password) {
			return fail(400, { message: 'settings.password_does_not_match' });
		}

		const passwordPolicy = await fetchPasswordPolicy(event.fetch, getServerEndpoint());
		if (!isPasswordLongEnough(password.toString(), passwordPolicy)) {
			return fail(400, {
				message: 'auth.password_too_short',
				values: { min: passwordPolicy.min_length }
			});
		}

		let csrfToken: string;
		try {
			csrfToken = await requireCsrf();
		} catch {
			return csrfFail();
		}

		const response = await djangoBrowserFetch(event, '/auth/browser/v1/auth/password/reset', {
			method: 'POST',
			csrfToken,
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ key, password })
		});

		let body: unknown = null;
		try {
			body = await response.json();
		} catch {
			body = null;
		}

		if (isPasswordResetSuccess(response, body)) {
			return redirect(302, '/login');
		}

		return fail(
			response.status,
			mapAllauthPasswordError(body as Parameters<typeof mapAllauthPasswordError>[0], {
				minLength: passwordPolicy.min_length,
				fallbackKey: 'auth.reset_failed'
			})
		);
	}
};
