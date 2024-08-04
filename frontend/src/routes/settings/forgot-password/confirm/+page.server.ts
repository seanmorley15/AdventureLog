import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const token = event.url.searchParams.get('token');
	const uid = event.url.searchParams.get('uid');

	return {
		props: {
			token,
			uid
		}
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	reset: async (event) => {
		const formData = await event.request.formData();

		const new_password1 = formData.get('new_password1') as string;
		const new_password2 = formData.get('new_password2') as string;
		const token = formData.get('token') as string;
		const uid = formData.get('uid') as string;

		if (!new_password1 || !new_password2) {
			return fail(400, { message: 'Password is required' });
		}

		if (new_password1 !== new_password2) {
			return fail(400, { message: 'Passwords do not match' });
		}

		if (!token || !uid) {
			return redirect(302, '/settings/forgot-password');
		} else {
			let response = await fetch(`${serverEndpoint}/auth/password/reset/confirm/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					token: token,
					uid: uid,
					new_password1,
					new_password2
				})
			});
			if (!response.ok) {
				let responseJson = await response.json();
				const key = Object.keys(responseJson)[0];
				return fail(response.status, { message: responseJson[key] });
			} else {
				return redirect(302, '/login');
			}
		}
	}
};
