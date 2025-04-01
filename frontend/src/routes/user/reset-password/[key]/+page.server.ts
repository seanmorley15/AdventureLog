import { fail, redirect } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';
import type { PageServerLoad, Actions } from './$types';

export const load = (async ({ params }) => {
	const key = params.key;
	if (!key) {
		throw redirect(302, '/');
	}
	return { key };
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

		const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
		const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
		const csrfToken = await fetchCSRFToken();

		const response = await event.fetch(`${serverEndpoint}/auth/browser/v1/auth/password/reset`, {
			headers: {
				'Content-Type': 'application/json',
				Cookie: `csrftoken=${csrfToken}`,
				'X-CSRFToken': csrfToken,
				Referer: event.url.origin // Include Referer header
			},
			method: 'POST',
			credentials: 'include',
			body: JSON.stringify({ key: key, password: password })
		});

		if (response.status !== 401) {
			const error_message = await response.json();
			console.error(error_message);
			console.log(response);
			return fail(response.status, { message: 'auth.reset_failed' });
		}

		return redirect(302, '/login');
	}
};
