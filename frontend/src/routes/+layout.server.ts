import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

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

	// Both badge counts arrive with the session lookup in the auth hook: no extra requests.
	const pendingInviteCount = event.locals.user ? (event.locals.pendingInviteCount ?? 0) : 0;
	const unreadCommentCount = event.locals.user ? (event.locals.unreadCommentCount ?? 0) : 0;

	if (event.locals.user) {
		return {
			user: event.locals.user,
			subscription,
			hasAccess,
			cloudMode,
			locale: event.locals.locale,
			pendingInviteCount,
			unreadCommentCount
		};
	}
	return {
		user: null,
		subscription,
		hasAccess,
		cloudMode,
		locale: event.locals.locale,
		pendingInviteCount,
		unreadCommentCount
	};
};
