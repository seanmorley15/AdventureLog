import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

export const load = (async (event) => {
	const id = event.params as { id: string };
	return redirect(301, `/locations/${id.id}`);
}) satisfies PageServerLoad;
