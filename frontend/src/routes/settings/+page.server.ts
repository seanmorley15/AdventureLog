import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from '../$types';
import type {
	APIKey,
	EndurainIntegration,
	ImmichIntegration,
	MediaUsage,
	User,
	WandererIntegration,
	AuthUserSession
} from '$lib/types';
import {
	clearSessionCookie,
	djangoBrowserFetch,
	djangoSessionFetch,
	djangoSessionJson,
	fetchCSRFToken,
	fetchPasswordPolicy,
	getServerEndpoint,
	isPasswordLongEnough,
	mapAllauthPasswordError,
	requireCsrf,
	requireUser
} from '$lib/index.server';

const endpoint = getServerEndpoint();

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

type EmailListResponse = {
	status: number;
	data: { email: string; verified: boolean; primary: boolean }[];
};

type SessionsListResponse = {
	status: number;
	data: AuthUserSession[];
};

type IntegrationsSummary = {
	google_maps: boolean;
	strava: { global: boolean; user: boolean };
	wanderer: { exists: boolean };
	endurain?: { exists: boolean };
};

type SocialProvider = {
	provider: string;
	url: string;
	name: string;
	usage_required: boolean;
};

export const load: PageServerLoad = async (event) => {
	requireUser(event);

	const sessionId = event.cookies.get('sessionid');
	if (!sessionId) {
		throw redirect(302, '/login');
	}

	// User profile is already hydrated in event.locals.user via the auth hook.
	// Fetch everything else in parallel instead of serial round-trips.
	const [
		emailResponse,
		mfaAuthenticatorResponse,
		integrations,
		publicUrlJson,
		socialProviders,
		immichIntegration,
		apiKeys,
		mediaUsage,
		passwordPolicy,
		wandererIntegration,
		endurainIntegration,
		sessionsResponse
	] = await Promise.all([
		djangoSessionJson<EmailListResponse>(event, '/auth/browser/v1/account/email'),
		djangoSessionJson<MFAAuthenticatorResponse>(event, '/auth/browser/v1/account/authenticators'),
		djangoSessionJson<IntegrationsSummary>(event, '/api/integrations/'),
		event
			.fetch(`${endpoint}/public-url/`)
			.then(async (res) => (res.ok ? ((await res.json()) as { PUBLIC_URL: string }) : null)),
		djangoSessionJson<SocialProvider[]>(event, '/auth/social-providers/').then(
			(data) => data ?? []
		),
		djangoSessionJson<ImmichIntegration>(event, '/api/integrations/immich/'),
		djangoSessionJson<APIKey[]>(event, '/auth/api-keys/').then((data) => data ?? []),
		djangoSessionJson<MediaUsage>(event, '/auth/user-media-usage/'),
		fetchPasswordPolicy(event.fetch, endpoint),
		djangoSessionJson<WandererIntegration>(event, '/api/integrations/wanderer/'),
		djangoSessionJson<EndurainIntegration>(event, '/api/integrations/endurain/'),
		djangoSessionJson<SessionsListResponse>(event, '/auth/browser/v1/auth/sessions')
	]);

	if (!emailResponse || !integrations || !publicUrlJson) {
		throw redirect(302, '/login');
	}

	const authenticators = (mfaAuthenticatorResponse?.data.length ?? 0) > 0;

	return {
		props: {
			emails: emailResponse.data,
			authenticators,
			immichIntegration,
			publicUrl: publicUrlJson.PUBLIC_URL,
			socialProviders,
			googleMapsEnabled: integrations.google_maps,
			stravaGlobalEnabled: integrations.strava.global,
			stravaUserEnabled: integrations.strava.user,
			wandererEnabled: integrations.wanderer.exists,
			wandererIntegration,
			endurainEnabled: integrations.endurain?.exists ?? false,
			endurainIntegration,
			apiKeys,
			mediaUsage,
			passwordPolicy,
			sessions: sessionsResponse?.data ?? []
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
			let measurement_system = formData.get('measurement_system') as string | null | undefined;
			let default_currency = formData.get('default_currency') as string | null | undefined;
			let map_style = formData.get('map_style') as string | null | undefined;

			const resCurrent = await djangoSessionFetch(event, '/auth/user-metadata/');

			if (!resCurrent.ok) {
				return fail(resCurrent.status, await resCurrent.json());
			}

			if (public_profile === 'on') {
				public_profile = true;
			} else {
				public_profile = false;
			}

			if (measurement_system === 'on') {
				measurement_system = 'imperial';
			} else {
				measurement_system = 'metric';
			}

			if (default_currency !== null && typeof default_currency === 'string') {
				default_currency = default_currency.trim().toUpperCase();
			}
			if (map_style !== null && typeof map_style === 'string') {
				map_style = map_style.trim();
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
			if (!default_currency || default_currency === currentUser.default_currency) {
				default_currency = undefined;
			}
			if (!map_style || map_style === currentUser.map_style) {
				map_style = undefined;
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
			formDataToSend.append('measurement_system', measurement_system.toString());
			if (default_currency) {
				formDataToSend.append('default_currency', default_currency);
			}
			if (map_style) {
				formDataToSend.append('map_style', map_style);
			}

			let csrfToken = await fetchCSRFToken();

			let res = await fetch(`${endpoint}/auth/update-user/`, {
				method: 'PATCH',
				headers: {
					Referer: event.url.origin,
					Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
					'X-CSRFToken': csrfToken
				},
				body: formDataToSend
			});

			let response = await res.json();

			if (!res.ok) {
				return fail(res.status, response);
			}

			return {
				success: true,
				left_shared_collections: response.left_shared_collections ?? 0,
				revoked_collection_invites: response.revoked_collection_invites ?? 0
			};
		} catch (error) {
			console.error('Error:', error);
			return { error: 'settings.generic_error' };
		}
	},
	changePassword: async (event) => {
		requireUser(event);
		let sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			return redirect(302, '/login');
		}

		const formData = await event.request.formData();

		const password1 = formData.get('password1') as string | null | undefined;
		const password2 = formData.get('password2') as string | null | undefined;
		let current_password = formData.get('current_password') as string | null | undefined;

		if (password1 !== password2) {
			return fail(400, { changePasswordError: 'settings.password_does_not_match' });
		}

		if (!current_password) {
			current_password = null;
		}

		const passwordPolicy = await fetchPasswordPolicy(event.fetch, endpoint);
		if (password1 && !isPasswordLongEnough(password1, passwordPolicy)) {
			return fail(400, {
				changePasswordError: 'auth.password_too_short',
				changePasswordValues: { min: passwordPolicy.min_length }
			});
		}

		let csrfToken: string;
		try {
			csrfToken = await requireCsrf();
		} catch {
			return fail(500, { changePasswordError: 'settings.csrf_failed' });
		}

		const body = current_password
			? { current_password, new_password: password1 }
			: { new_password: password1 };

		const res = await djangoBrowserFetch(event, '/auth/browser/v1/account/password/change', {
			method: 'POST',
			csrfToken,
			sessionId,
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});

		if (!res.ok) {
			const errorResponse = await res.json();
			const mapped = mapAllauthPasswordError(errorResponse, {
				minLength: passwordPolicy.min_length
			});
			return fail(res.status, {
				changePasswordError: mapped.message,
				changePasswordValues: mapped.values
			});
		}

		try {
			await djangoBrowserFetch(event, '/auth/browser/v1/auth/session', {
				method: 'DELETE',
				csrfToken,
				sessionId,
				headers: { 'Content-Type': 'application/json' }
			});
		} catch {
			// Still clear the local session after a successful password change.
		}

		clearSessionCookie(event);
		throw redirect(303, '/login');
	},
	restoreData: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		let sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			return redirect(302, '/');
		}

		try {
			const formData = await event.request.formData();
			const file = formData.get('file') as File | null | undefined;
			const confirm = formData.get('confirm') as string | null | undefined;

			if (!file || file.size === 0) {
				return fail(400, { message: 'settings.no_file_selected' });
			}

			if (confirm !== 'yes') {
				return fail(400, { message: 'settings.confirmation_required' });
			}

			let csrfToken = await fetchCSRFToken();

			const apiFormData = new FormData();
			apiFormData.append('file', file);
			apiFormData.append('confirm', 'yes');

			let res = await fetch(`${endpoint}/api/backup/import/`, {
				method: 'POST',
				headers: {
					Referer: event.url.origin,
					Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
					'X-CSRFToken': csrfToken
				},
				body: apiFormData
			});

			if (!res.ok) {
				const errorData = await res.json();
				return fail(res.status, {
					message: errorData.code
						? `settings.restore_error_${errorData.code}`
						: 'settings.generic_error',
					details: errorData
				});
			}

			return { success: true };
		} catch (error) {
			console.error('Restore error:', error);
			return fail(500, { message: 'settings.generic_error' });
		}
	},
	deleteAccount: async (event) => {
		if (!event.locals.user) {
			return redirect(302, '/');
		}
		const sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			return redirect(302, '/');
		}

		const formData = await event.request.formData();
		const confirmation = (formData.get('confirmation') as string | null)?.trim() ?? '';
		const password = (formData.get('password') as string | null)?.trim() ?? '';

		const csrfToken = await fetchCSRFToken();
		const body: { confirmation: string; password?: string } = { confirmation };
		if (password) {
			body.password = password;
		}

		const res = await fetch(`${endpoint}/auth/delete-account/`, {
			method: 'POST',
			headers: {
				Referer: event.url.origin,
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
				'X-CSRFToken': csrfToken,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(body)
		});

		if (res.status === 204) {
			clearSessionCookie(event);
			throw redirect(303, '/');
		}

		const error = await res.json().catch(() => ({}));
		if (error.confirmation || error.password) {
			const messages = [error.confirmation, error.password].filter(Boolean).flat();
			return fail(res.status, {
				deleteAccountError: messages[0] || 'settings.delete_account_error'
			});
		}
		if (res.status === 403) {
			return fail(403, { deleteAccountError: 'settings.delete_account_staff_blocked' });
		}
		return fail(res.status, {
			deleteAccountError: error.detail || 'settings.delete_account_error'
		});
	}
};
