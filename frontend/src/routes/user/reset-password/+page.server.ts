import { csrfFail, djangoBrowserFetch, requireCsrf } from '$lib/index.server';
import { fail, type Actions } from '@sveltejs/kit';

export const actions: Actions = {
	forgotPassword: async (event) => {
		const formData = await event.request.formData();
		const email = formData.get('email') as string | null | undefined;

		if (!email?.trim()) {
			return fail(400, { message: 'auth.email_required' });
		}

		let csrfToken: string;
		try {
			csrfToken = await requireCsrf();
		} catch {
			return csrfFail();
		}

		const res = await djangoBrowserFetch(event, '/auth/browser/v1/auth/password/request', {
			method: 'POST',
			csrfToken,
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: email.trim() })
		});

		if (!res.ok) {
			return fail(res.status, { message: 'auth.reset_request_failed' });
		}

		return { success: true };
	}
};
