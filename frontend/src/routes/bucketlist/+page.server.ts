const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { PageServerLoad, Actions } from './$types';
import { fail, redirect } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';

const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch, locals, url, cookies }) => {
	if (!locals.user) {
		return {
			props: {
				bucketItems: [],
				count: 0
			}
		};
	}

	try {
		const page = url.searchParams.get('page') || '1';
		const status = url.searchParams.get('status') || 'all';

		let apiUrl = `${endpoint}/api/bucketlist/items/?page=${page}`;
		if (status !== 'all') {
			apiUrl += `&status=${status}`;
		}

		const res = await fetch(apiUrl, {
			method: 'GET',
			headers: {
				Cookie: `sessionid=${cookies.get('sessionid')}`
			},
			credentials: 'include'
		});

		if (res.ok) {
			const data = await res.json();
			return {
				props: {
					bucketItems: Array.isArray(data) ? data : data.results || [],
					count: data.count || (Array.isArray(data) ? data.length : 0)
				}
			};
		}
	} catch (e) {
		console.error('Failed to load bucket list items:', e);
	}

	return {
		props: {
			bucketItems: [],
			count: 0
		}
	};
};
