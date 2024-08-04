import { fail, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	const token = event.url.searchParams.get('token');
	const uid = event.url.searchParams.get('uid');
	console.log('token', token);

	if (!token) {
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
				new_password1: 'password',
				new_password2: 'password'
			})
		});
		let data = await response.json();
		console.log('data', data);
	}

	return {};
}) satisfies PageServerLoad;
