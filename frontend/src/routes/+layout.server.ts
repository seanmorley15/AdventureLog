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

	if (event.locals.user) {
		return {
			user: event.locals.user,
			subscription,
			hasAccess,
			cloudMode,
			locale: event.locals.locale
		};
	}
	return {
		user: null,
		subscription,
		hasAccess,
		cloudMode,
		locale: event.locals.locale
	};
};
