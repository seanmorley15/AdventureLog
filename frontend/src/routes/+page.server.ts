const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import { redirect, type Actions } from '@sveltejs/kit';
import { themes } from '$lib';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const actions: Actions = {
	setTheme: async ({ url, cookies }) => {
		const theme = url.searchParams.get('theme');
		// change the theme only if it is one of the allowed themes
		if (theme && themes.find((t) => t.name === theme)) {
			cookies.set('colortheme', theme, {
				path: '/',
				maxAge: 60 * 60 * 24 * 365, // 1 year
				sameSite: 'lax'
			});
		}
	},
	logout: async ({ cookies }: { cookies: any }) => {
		const cookie = cookies.get('auth') || null;

		if (!cookie) {
			return;
		}

		const res = await fetch(`${serverEndpoint}/auth/logout/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Cookie: cookies.get('auth')
			}
		});
		if (res.ok) {
			cookies.delete('auth', { path: '/', secure: false });
			cookies.delete('refresh', { path: '/', secure: false });
			return redirect(302, '/login');
		} else {
			return redirect(302, '/');
		}
	},
	setLocale: async ({ url, cookies }) => {
		const locale = url.searchParams.get('locale');
		// change the locale only if it is one of the allowed locales
		if (locale) {
			cookies.set('locale', locale, {
				path: '/',
				maxAge: 60 * 60 * 24 * 365 // 1 year
			});
		}
	}
};
