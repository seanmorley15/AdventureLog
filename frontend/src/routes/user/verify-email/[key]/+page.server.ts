import { redirect } from '@sveltejs/kit';
import { djangoBrowserFetch, requireCsrf, setSessionFromResponse } from '$lib/index.server';
import type { PageServerLoad } from './$types';

export const load = (async (event) => {
	const key = event.params.key;
	if (!key) {
		return { verified: false };
	}

	let csrfToken: string;
	try {
		csrfToken = await requireCsrf();
	} catch {
		return { verified: false };
	}

	const verifyFetch = await djangoBrowserFetch(event, '/auth/browser/v1/auth/email/verify', {
		method: 'POST',
		csrfToken,
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ key })
	});

	// 200: verified and authenticated (pending login/signup stage continued).
	// 401: verified successfully but not logged in (typical when opening the email link).
	if (verifyFetch.ok) {
		setSessionFromResponse(event, verifyFetch);
		throw redirect(302, '/');
	}

	if (verifyFetch.status === 401) {
		return { verified: true };
	}

	try {
		const errorMessage = await verifyFetch.json();
		console.error('Failed to verify email', errorMessage);
	} catch {
		console.error('Failed to verify email');
	}

	return { verified: false };
}) satisfies PageServerLoad;
