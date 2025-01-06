import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from '../$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { ImmichIntegration, User } from '$lib/types';
import { fetchCSRFToken } from '$lib/index.server';
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

type MFAAuthenticatorResponse = {
	status: number;
	data: {
		type: string;
		created_at: number;
		last_used_at: number | null;
		total_code_count?: number;
		unused_code_count?: number;
	}[];
};

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/');
	}
	let sessionId = event.cookies.get('sessionid');
	if (!sessionId) {
		return redirect(302, '/');
	}
	let res = await fetch(`${endpoint}/auth/user-metadata/`, {
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	let user = (await res.json()) as User;

	let emailFetch = await fetch(`${endpoint}/_allauth/browser/v1/account/email`, {
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	let emailResponse = (await emailFetch.json()) as {
		status: number;
		data: { email: string; verified: boolean; primary: boolean }[];
	};
	let emails = emailResponse.data;
	if (!res.ok || !emailFetch.ok) {
		return redirect(302, '/');
	}

	let mfaAuthenticatorFetch = await fetch(
		`${endpoint}/_allauth/browser/v1/account/authenticators`,
		{
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		}
	);
	let mfaAuthenticatorResponse = (await mfaAuthenticatorFetch.json()) as MFAAuthenticatorResponse;
	let authenticators = (mfaAuthenticatorResponse.data.length > 0) as boolean;

	let immichIntegration: ImmichIntegration | null = null;
	let immichIntegrationsFetch = await fetch(`${endpoint}/api/integrations/immich/`, {
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	if (immichIntegrationsFetch.ok) {
		immichIntegration = await immichIntegrationsFetch.json();
	}

	let publicUrlFetch = await fetch(`${endpoint}/public-url/`);
	let publicUrl = '';
	if (!publicUrlFetch.ok) {
		return redirect(302, '/');
	} else {
		let publicUrlJson = await publicUrlFetch.json();
		publicUrl = publicUrlJson.PUBLIC_URL;
	}

	return {
		props: {
			user,
			emails,
			authenticators,
			immichIntegration,
			publicUrl
		}
	};
};

export const actions: Actions = {
	changeDetails: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		let sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			return redirect(302, '/');
		}

		try {
			const formData = await event.request.formData();

			let username = formData.get('username') as string | null | undefined;
			let first_name = formData.get('first_name') as string | null | undefined;
			let last_name = formData.get('last_name') as string | null | undefined;
			let profile_pic = formData.get('profile_pic') as File | null | undefined;
			let public_profile = formData.get('public_profile') as string | null | undefined | boolean;

			const resCurrent = await fetch(`${endpoint}/auth/user-metadata/`, {
				headers: {
					Cookie: `sessionid=${sessionId}`
				}
			});

			if (!resCurrent.ok) {
				return fail(resCurrent.status, await resCurrent.json());
			}

			// Gets the boolean value of the public_profile input
			if (public_profile === 'on') {
				public_profile = true;
			} else {
				public_profile = false;
			}

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

			let csrfToken = await fetchCSRFToken();

			let res = await fetch(`${endpoint}/auth/update-user/`, {
				method: 'PATCH',
				headers: {
					Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
					'X-CSRFToken': csrfToken
				},
				body: formDataToSend
			});

			let response = await res.json();

			if (!res.ok) {
				return fail(res.status, response);
			}

			return { success: true };
		} catch (error) {
			console.error('Error:', error);
			return { error: 'settings.generic_error' };
		}
	},
	changePassword: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		let sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			return redirect(302, '/');
		}

		const formData = await event.request.formData();

		const password1 = formData.get('password1') as string | null | undefined;
		const password2 = formData.get('password2') as string | null | undefined;
		let current_password = formData.get('current_password') as string | null | undefined;

		if (password1 !== password2) {
			return fail(400, { message: 'settings.password_does_not_match' });
		}
		if (!current_password) {
			current_password = null;
		}

		let csrfToken = await fetchCSRFToken();

		if (current_password) {
			let res = await fetch(`${endpoint}/_allauth/browser/v1/account/password/change`, {
				method: 'POST',
				headers: {
					Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
					'X-CSRFToken': csrfToken,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					current_password,
					new_password: password1
				})
			});
			if (!res.ok) {
				return fail(res.status, { message: 'settings.error_change_password' });
			}
			return { success: true };
		} else {
			let res = await fetch(`${endpoint}/_allauth/browser/v1/account/password/change`, {
				method: 'POST',
				headers: {
					Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
					'X-CSRFToken': csrfToken,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					new_password: password1
				})
			});
			if (!res.ok) {
				console.log('Error:', await res.json());
				return fail(res.status, { message: 'settings.error_change_password' });
			}
			return { success: true };
		}
	},
	changeEmail: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		let sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			return redirect(302, '/');
		}
		const formData = await event.request.formData();
		const new_email = formData.get('new_email') as string | null | undefined;
		if (!new_email) {
			return fail(400, { message: 'auth.email_required' });
		} else {
			let csrfToken = await fetchCSRFToken();
			let res = await fetch(`${endpoint}/auth/change-email/`, {
				method: 'POST',
				headers: {
					Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
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
