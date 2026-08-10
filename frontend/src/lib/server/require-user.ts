import { redirect } from '@sveltejs/kit';
import type { RequestEvent } from '@sveltejs/kit';

/** Redirect unauthenticated visitors to login. */
export function requireUser(event: Pick<RequestEvent, 'locals' | 'url'>) {
	if (!event.locals.user) {
		const next = event.url.pathname + event.url.search;
		const loginUrl =
			next && next !== '/login' ? `/login?next=${encodeURIComponent(next)}` : '/login';
		throw redirect(302, loginUrl);
	}
}
