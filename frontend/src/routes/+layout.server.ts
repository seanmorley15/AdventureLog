import { locale } from 'svelte-i18n';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
	if (event.locals.user) {
		return {
			user: event.locals.user,
			locale: event.locals.locale
		};
	}
	return {
		user: null,
		locale: event.locals.locale
	};
};
