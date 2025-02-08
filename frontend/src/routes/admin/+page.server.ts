import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from '../$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load: PageServerLoad = async (event) => {
	let publicUrlFetch = await fetch(`${endpoint}/public-url/`);
	let publicUrl = '';
	if (!publicUrlFetch.ok) {
		return redirect(302, '/');
	} else {
		let publicUrlJson = await publicUrlFetch.json();
		publicUrl = publicUrlJson.PUBLIC_URL;
	}

	return redirect(302, publicUrl + '/admin/');
};
