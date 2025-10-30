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

export const actions = {
	create: async ({ request, fetch, locals, cookies }) => {
		console.log('Create action called');
		console.log('User:', locals.user);
		
		if (!locals.user) {
			console.log('User not authenticated');
			return fail(401, { error: 'Unauthorized - Please log in first' });
		}

		const formData = await request.formData();
		const title = formData.get('title')?.toString();
		const description = formData.get('description')?.toString() || '';
		const tags = formData.get('tags')?.toString() || '';
		const status = formData.get('status')?.toString() || 'planned';
		const notes = formData.get('notes')?.toString() || '';

		console.log('Form data:', { title, description, tags, status, notes });

		if (!title) {
			return fail(400, { error: 'Title is required' });
		}

		try {
			const csrfToken = await fetchCSRFToken();
			
			const payload = {
				title: title.trim(),
				description: description.trim(),
				tags: tags.trim() ? tags.split(',').map(t => t.trim()) : [],
				status,
				notes: notes.trim(),
				is_public: false
			};
			
			console.log('Sending payload:', JSON.stringify(payload));

			const response = await fetch(`${endpoint}/api/bucketlist/items/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken,
					Cookie: `sessionid=${cookies.get('sessionid')}; csrftoken=${csrfToken}`
				},
				credentials: 'include',
				body: JSON.stringify(payload)
			});

			console.log('Response status:', response.status);

			if (!response.ok) {
				const error = await response.text();
				console.log('Error response:', error);
				return fail(response.status, { error: `Failed to create item: ${error}` });
			}

			const result = await response.json();
			console.log('Success! Created item:', result);
			return { success: true };
		} catch (error) {
			console.error('Exception:', error);
			return fail(500, { error: 'Failed to create item: ' + error });
		}
	},

	delete: async ({ request, fetch, locals, cookies }) => {
		if (!locals.user) {
			return fail(401, { error: 'Unauthorized' });
		}

		const formData = await request.formData();
		const id = formData.get('id')?.toString();

		if (!id) {
			return fail(400, { error: 'ID is required' });
		}

		try {
			const csrfToken = await fetchCSRFToken();
			
			const response = await fetch(`${endpoint}/api/bucketlist/items/${id}/`, {
				method: 'DELETE',
				headers: {
					'X-CSRFToken': csrfToken,
					Cookie: `sessionid=${cookies.get('sessionid')}; csrftoken=${csrfToken}`
				},
				credentials: 'include'
			});

			if (!response.ok) {
				return fail(response.status, { error: 'Failed to delete item' });
			}

			return { success: true };
		} catch (error) {
			return fail(500, { error: 'Failed to delete item' });
		}
	}
} satisfies Actions;
