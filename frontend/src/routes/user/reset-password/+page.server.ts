import { fetchCSRFToken } from '$lib/index.server';
import { fail, type Actions } from '@sveltejs/kit';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const actions: Actions = {
	forgotPassword: async (event) => {
		const formData = await event.request.formData();

		const email = formData.get('email') as string | null | undefined;

		if (!email) {
			return fail(400, { message: 'missing_email' });
		}

		let csrfToken = await fetchCSRFToken();

		let res = await fetch(`${endpoint}/auth/browser/v1/auth/password/request`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken,
				Cookie: `csrftoken=${csrfToken}`,
				Referer: event.url.origin // Include Referer header
			},
			body: JSON.stringify({
				email
			})
		});

		if (!res.ok) {
			let message = await res.json();
			return fail(res.status, message);
		}
		return { success: true };
	}
};
