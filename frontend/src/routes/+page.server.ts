import { redirect, type Actions } from '@sveltejs/kit';
import { getRandomBackground, themes } from '$lib';
import { clearSessionCookie, djangoBrowserFetch } from '$lib/index.server';
import type { PageServerLoad } from './$types';

export const load = (async (event) => {
	if (event.locals.user) {
		return redirect(302, '/dashboard');
	} else {
		const background = getRandomBackground();
		return {
			props: {
				background
			}
		};
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	setTheme: async ({ url, cookies }) => {
		const theme = url.searchParams.get('theme');
		if (theme && themes.find((t) => t.name === theme)) {
			cookies.set('colortheme', theme, {
				path: '/',
				maxAge: 60 * 60 * 24 * 365,
				sameSite: 'lax',
				secure: url.protocol === 'https:'
			});
		}
	},
	logout: async (event) => {
		const sessionId = event.cookies.get('sessionid');

		if (!sessionId) {
			return redirect(302, '/');
		}

		try {
			await djangoBrowserFetch(event, '/auth/browser/v1/auth/session', {
				method: 'DELETE',
				headers: { 'Content-Type': 'application/json' }
			});
		} catch {
			// Still clear the local cookie even if the backend session delete fails.
		}

		clearSessionCookie(event);
		return redirect(302, '/');
	},
	setLocale: async ({ url, cookies }) => {
		const locale = url.searchParams.get('locale');
		if (locale) {
			cookies.set('locale', locale, {
				path: '/',
				maxAge: 60 * 60 * 24 * 365
			});
		}
	}
};
