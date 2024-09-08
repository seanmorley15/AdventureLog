import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from '../$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { User } from '$lib/types';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/');
	}
	if (!event.cookies.get('auth')) {
		return redirect(302, '/');
	}
	let res = await fetch(`${endpoint}/auth/user/`, {
		headers: {
			Cookie: event.cookies.get('auth') || ''
		}
	});
	let user = (await res.json()) as User;

	if (!res.ok) {
		return redirect(302, '/');
	}

	return {
		props: {
			user
		}
	};
};

export const actions: Actions = {
	changeDetails: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		if (!event.cookies.get('auth')) {
			return redirect(302, '/');
		}

		try {
			const formData = await event.request.formData();

			let username = formData.get('username') as string | null | undefined;
			let first_name = formData.get('first_name') as string | null | undefined;
			let last_name = formData.get('last_name') as string | null | undefined;
			let profile_pic = formData.get('profile_pic') as File | null | undefined;
			let public_profile = formData.get('public_profile') as string | null | undefined | boolean;

			const resCurrent = await fetch(`${endpoint}/auth/user/`, {
				headers: {
					Cookie: event.cookies.get('auth') || ''
				}
			});

			if (!resCurrent.ok) {
				return fail(resCurrent.status, await resCurrent.json());
			}

			if (public_profile === 'on') {
				public_profile = true;
			} else {
				public_profile = false;
			}
			console.log(public_profile);

			let currentUser = (await resCurrent.json()) as User;

			if (username === currentUser.username || !username) {
				username = undefined;
			}
			if (first_name === currentUser.first_name || !first_name) {
				first_name = undefined;
			}
			if (last_name === currentUser.last_name || !last_name) {
				last_name = undefined;
			}
			if (currentUser.profile_pic && profile_pic?.size === 0) {
				profile_pic = undefined;
			}

			let formDataToSend = new FormData();
			if (username) {
				formDataToSend.append('username', username);
			}
			if (first_name) {
				formDataToSend.append('first_name', first_name);
			}
			if (last_name) {
				formDataToSend.append('last_name', last_name);
			}
			if (profile_pic) {
				formDataToSend.append('profile_pic', profile_pic);
			}
			formDataToSend.append('public_profile', public_profile.toString());

			let res = await fetch(`${endpoint}/auth/user/`, {
				method: 'PATCH',
				headers: {
					Cookie: event.cookies.get('auth') || ''
				},
				body: formDataToSend
			});

			let response = await res.json();

			if (!res.ok) {
				// change the first key in the response to 'message' for the fail function
				response = { message: Object.values(response)[0] };
				return fail(res.status, response);
			}

			return { success: true };
		} catch (error) {
			console.error('Error:', error);
			return { error: 'An error occurred while processing your request.' };
		}
	},
	changePassword: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		if (!event.cookies.get('auth')) {
			return redirect(302, '/');
		}
		console.log('changePassword');
		const formData = await event.request.formData();

		const password1 = formData.get('password1') as string | null | undefined;
		const password2 = formData.get('password2') as string | null | undefined;

		if (password1 !== password2) {
			return fail(400, { message: 'Passwords do not match' });
		}

		let res = await fetch(`${endpoint}/auth/password/change/`, {
			method: 'POST',
			headers: {
				Cookie: event.cookies.get('auth') || '',
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				new_password1: password1,
				new_password2: password2
			})
		});
		if (!res.ok) {
			return fail(res.status, await res.json());
		}
		return { success: true };
	},
	changeEmail: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		if (!event.cookies.get('auth')) {
			return redirect(302, '/');
		}
		const formData = await event.request.formData();
		const new_email = formData.get('new_email') as string | null | undefined;
		if (!new_email) {
			return fail(400, { message: 'Email is required' });
		} else {
			let res = await fetch(`${endpoint}/auth/change-email/`, {
				method: 'POST',
				headers: {
					Cookie: event.cookies.get('auth') || '',
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					new_email
				})
			});
			if (!res.ok) {
				return fail(res.status, await res.json());
			}
			return { success: true };
		}
	}
};
