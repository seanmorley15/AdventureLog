import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

async function fetchPendingInviteCount(event: Parameters<LayoutServerLoad>[0]): Promise<number> {
	const sessionId = event.cookies.get('sessionid');
	if (!sessionId) {
		return 0;
	}

	try {
		const res = await event.fetch(`${serverEndpoint}/api/collections/invites/`, {
			headers: { Cookie: `sessionid=${sessionId}` }
		});

		if (!res.ok) {
			return 0;
		}

		const invites = await res.json();
		return Array.isArray(invites) ? invites.length : 0;
	} catch {
		return 0;
	}
}

export const load: LayoutServerLoad = async (event) => {
	const cloudMode = event.locals.cloudMode ?? false;
	const hasAccess = event.locals.hasAccess ?? true;
	const subscription = event.locals.subscription ?? null;
	const path = event.url.pathname;
	const allowList = [
		'/subscribe',
		'/login',
		'/signup',
		'/user/reset-password',
		'/user/verify-email'
	];
	const isAllowed = allowList.some((allowed) => path.startsWith(allowed));

	if (cloudMode && event.locals.user && !hasAccess && !isAllowed) {
		throw redirect(302, '/subscribe');
	}

	const pendingInviteCount = event.locals.user ? await fetchPendingInviteCount(event) : 0;

	if (event.locals.user) {
		return {
			user: event.locals.user,
			subscription,
			hasAccess,
			cloudMode,
			locale: event.locals.locale,
			pendingInviteCount
		};
	}
	return {
		user: null,
		subscription,
		hasAccess,
		cloudMode,
		locale: event.locals.locale,
		pendingInviteCount
	};
};
