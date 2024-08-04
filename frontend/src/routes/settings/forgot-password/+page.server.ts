import { fail, type Actions } from '@sveltejs/kit';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const actions: Actions = {
	forgotPassword: async (event) => {
		const formData = await event.request.formData();

		const email = formData.get('email') as string | null | undefined;

		if (!email) {
			return fail(400, { message: 'Email is required' });
		}

		let res = await fetch(`${endpoint}/auth/password/reset/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				email
			})
		});

		if (!res.ok) {
			let message = await res.json();

			const key = Object.keys(message)[0];

			return fail(res.status, { message: message[key] });
		}
		return { success: true };
	}
};
