import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure, Collection } from '$lib/types';

import type { Actions, RequestEvent } from '@sveltejs/kit';
import { fetchCSRFToken } from '$lib/index.server';
import { checkLink } from '$lib';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let next = null;
		let previous = null;
		let count = 0;
		let adventures: Adventure[] = [];
		let sessionId = event.cookies.get('sessionid');
		let initialFetch = await fetch(`${serverEndpoint}/api/collections/?order_by=updated_at`, {
			headers: {
				Cookie: `sessionid=${sessionId}`
			},
			credentials: 'include'
		});
		if (!initialFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let visited = res.results as Adventure[];
			next = res.next;
			previous = res.previous;
			count = res.count;
			adventures = [...adventures, ...visited];
		}

		return {
			props: {
				adventures,
				next,
				previous,
				count
			}
		};
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();

		const name = formData.get('name') as string;
		const description = formData.get('description') as string | null;
		const start_date = formData.get('start_date') as string | null;
		const end_date = formData.get('end_date') as string | null;
		let link = formData.get('link') as string | null;

		if (link) {
			link = checkLink(link);
		}

		if (!name) {
			return {
				status: 400,
				body: { error: 'Missing required fields' }
			};
		}

		const formDataToSend = new FormData();
		formDataToSend.append('name', name);
		formDataToSend.append('description', description || '');
		formDataToSend.append('start_date', start_date || '');
		formDataToSend.append('end_date', end_date || '');
		formDataToSend.append('link', link || '');
		let sessionid = event.cookies.get('sessionid');

		if (!sessionid) {
			return {
				status: 401,
				body: { message: 'Unauthorized' }
			};
		}

		const csrfToken = await fetchCSRFToken();

		if (!csrfToken) {
			return {
				status: 500,
				body: { message: 'Failed to fetch CSRF token' }
			};
		}

		const res = await fetch(`${serverEndpoint}/api/collections/`, {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken,
				Referer: event.url.origin, // Include Referer header
				Cookie: `sessionid=${sessionid}; csrftoken=${csrfToken}`
			},
			body: formDataToSend
		});

		let new_id = await res.json();

		if (!res.ok) {
			const errorBody = await res.json();
			return {
				status: res.status,
				body: { error: errorBody }
			};
		}

		let id = new_id.id;
		let user_id = new_id.user_id;

		return { id, user_id };
	},
	edit: async (event) => {
		const formData = await event.request.formData();

		const collectionId = formData.get('adventureId') as string;
		const name = formData.get('name') as string;
		const description = formData.get('description') as string | null;
		let is_public = formData.get('is_public') as string | null | boolean;
		const start_date = formData.get('start_date') as string | null;
		const end_date = formData.get('end_date') as string | null;
		let link = formData.get('link') as string | null;

		if (is_public) {
			is_public = true;
		} else {
			is_public = false;
		}

		if (link) {
			link = checkLink(link);
		}

		if (!name) {
			return {
				status: 400,
				body: { error: 'Missing name.' }
			};
		}

		const formDataToSend = new FormData();
		formDataToSend.append('name', name);
		formDataToSend.append('description', description || '');
		formDataToSend.append('is_public', is_public.toString());
		formDataToSend.append('start_date', start_date || '');
		formDataToSend.append('end_date', end_date || '');
		formDataToSend.append('link', link || '');

		let sessionId = event.cookies.get('sessionid');

		if (!sessionId) {
			return {
				status: 401,
				body: { message: 'Unauthorized' }
			};
		}

		const csrfToken = await fetchCSRFToken();

		if (!csrfToken) {
			return {
				status: 500,
				body: { message: 'Failed to fetch CSRF token' }
			};
		}

		const res = await fetch(`${serverEndpoint}/api/collections/${collectionId}/`, {
			method: 'PATCH',
			headers: {
				'X-CSRFToken': csrfToken,
				Cookie: `sessionid=${sessionId}; csrftoken=${csrfToken}`,
				Referer: event.url.origin // Include Referer header
			},
			body: formDataToSend,

			credentials: 'include'
		});

		if (!res.ok) {
			const errorBody = await res.json();
			return {
				status: res.status,
				body: { error: errorBody }
			};
		}

		return {
			status: 200
		};
	},
	get: async (event) => {
		if (!event.locals.user) {
			return {
				status: 401,
				body: { message: 'Unauthorized' }
			};
		}

		const formData = await event.request.formData();

		const order_direction = formData.get('order_direction') as string;
		const order_by = formData.get('order_by') as string;

		console.log(order_direction, order_by);

		let adventures: Adventure[] = [];

		if (!event.locals.user) {
			return {
				status: 401,
				body: { message: 'Unauthorized' }
			};
		}

		let next = null;
		let previous = null;
		let count = 0;

		let collectionsFetch = await fetch(
			`${serverEndpoint}/api/collections/?order_by=${order_by}&order_direction=${order_direction}`,
			{
				headers: {
					Cookie: `sessionid=${event.cookies.get('sessionid')}`
				},
				credentials: 'include'
			}
		);
		if (!collectionsFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await collectionsFetch.json();
			let visited = res.results as Adventure[];
			next = res.next;
			previous = res.previous;
			count = res.count;
			adventures = [...adventures, ...visited];
			console.log(next, previous, count);
		}

		return {
			adventures,
			next,
			previous,
			count
		};
	},
	changePage: async (event) => {
		const formData = await event.request.formData();
		const next = formData.get('next') as string;
		const previous = formData.get('previous') as string;
		const page = formData.get('page') as string;

		if (!event.locals.user) {
			return {
				status: 401,
				body: { message: 'Unauthorized' }
			};
		}

		if (!page) {
			return {
				status: 400,
				body: { error: 'Missing required fields' }
			};
		}

		// Start with the provided URL or default to the filtered adventures endpoint
		let url: string = next || previous || '/api/collections/';

		// Extract the path starting from '/api/adventures'
		const apiIndex = url.indexOf('/api/collections');
		if (apiIndex !== -1) {
			url = url.slice(apiIndex);
		} else {
			url = '/api/collections/';
		}

		// Replace or add the page number in the URL
		if (url.includes('page=')) {
			url = url.replace(/page=\d+/, `page=${page}`);
		} else {
			// If 'page=' is not in the URL, add it
			url += url.includes('?') ? '&' : '?';
			url += `page=${page}`;
		}

		const fullUrl = `${serverEndpoint}${url}`;

		let sessionId = event.cookies.get('sessionid');

		try {
			const response = await fetch(fullUrl, {
				headers: {
					'Content-Type': 'application/json',
					Cookie: `sessionid=${sessionId}`
				},
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			const data = await response.json();
			let adventures = data.results as Adventure[];
			let next = data.next;
			let previous = data.previous;
			let count = data.count;

			return {
				status: 200,
				body: {
					adventures,
					next,
					previous,
					count,
					page
				}
			};
		} catch (error) {
			console.error('Error fetching data:', error);
			return {
				status: 500,
				body: { error: 'Failed to fetch data' }
			};
		}
	}
};
