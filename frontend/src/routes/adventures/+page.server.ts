import { redirect } from '@sveltejs/kit';

export const load = (async (_event) => {
	return redirect(301, '/locations');
}) satisfies import('./$types').PageServerLoad;
