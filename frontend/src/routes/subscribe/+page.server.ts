import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { fetchCSRFToken } from '$lib/index.server';
import type { MediaUsage } from '$lib/types';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load: PageServerLoad = async (event) => {
	if (!event.locals.user) {
		throw redirect(302, '/login');
	}

	const sessionId = event.cookies.get('sessionid');
	let mediaUsage: MediaUsage | null = null;

	if (sessionId) {
		const mediaUsageFetch = await event.fetch(`${endpoint}/auth/user-media-usage/`, {
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		});
		if (mediaUsageFetch.ok) {
			mediaUsage = (await mediaUsageFetch.json()) as MediaUsage;
		}
	}

	return {
		user: event.locals.user,
		subscription: event.locals.subscription,
		hasAccess: event.locals.hasAccess,
		cloudMode: event.locals.cloudMode,
		mediaUsage
	};
};

export const actions: Actions = {
	subscribe: async (event) => {
		if (!event.locals.user) {
			throw redirect(302, '/login');
		}

		const sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			throw redirect(302, '/login');
		}

		const csrfToken = await fetchCSRFToken();
		if (!csrfToken) {
			return fail(500, { message: 'Unable to start checkout.', action: 'subscribe' });
		}

		const res = await event.fetch(`${endpoint}/api/billing/create-checkout-session/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken,
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`
			},
			body: JSON.stringify({})
		});

		if (!res.ok) {
			const error = await res.json().catch(() => ({}));
			return fail(res.status, {
				message: error.detail || 'Unable to start checkout.',
				action: 'subscribe'
			});
		}

		const data = await res.json();
		if (!data.url) {
			return fail(500, { message: 'Missing checkout URL.', action: 'subscribe' });
		}

		throw redirect(303, data.url);
	},
	manageBilling: async (event) => {
		if (!event.locals.user) {
			throw redirect(302, '/login');
		}

		const sessionId = event.cookies.get('sessionid');
		if (!sessionId) {
			throw redirect(302, '/login');
		}

		const csrfToken = await fetchCSRFToken();
		if (!csrfToken) {
			return fail(500, { message: 'Unable to open billing portal.', action: 'portal' });
		}

		const res = await event.fetch(`${endpoint}/api/billing/create-portal-session/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': csrfToken,
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`
			},
			body: JSON.stringify({})
		});

		if (!res.ok) {
			const error = await res.json().catch(() => ({}));
			return fail(res.status, {
				message: error.detail || 'Unable to open billing portal.',
				action: 'portal'
			});
		}

		const data = await res.json();
		if (!data.url) {
			return fail(500, { message: 'Missing billing portal URL.', action: 'portal' });
		}

		throw redirect(303, data.url);
	}
};
