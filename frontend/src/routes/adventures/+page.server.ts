import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
import type { Adventure } from '$lib/types';

import type { Actions, RequestEvent } from '@sveltejs/kit';
import { fetchCSRFToken, tryRefreshToken } from '$lib/index.server';
import { checkLink } from '$lib';

const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	} else {
		let count = 0;
		let adventures: Adventure[] = [];

		const visited = event.url.searchParams.get('visited');
		const planned = event.url.searchParams.get('planned');

		let typeString: string = '';

		if (visited == 'on') {
			typeString += 'visited';
		}
		if (planned == 'on') {
			if (typeString) {
				typeString += ',';
			}
			typeString += 'planned';
		} else if (!visited && !planned) {
			typeString = 'visited,planned';
		}

		const include_collections = event.url.searchParams.get('include_collections') || 'false';
		const order_by = event.url.searchParams.get('order_by') || 'updated_at';
		const order_direction = event.url.searchParams.get('order_direction') || 'asc';
		const page = event.url.searchParams.get('page') || '1';

		let initialFetch = await fetch(
			`${serverEndpoint}/api/adventures/filtered?types=${typeString}&order_by=${order_by}&order_direction=${order_direction}&include_collections=${include_collections}&page=${page}`,
			{
				headers: {
					Cookie: `${event.cookies.get('auth')}`
				}
			}
		);
		if (!initialFetch.ok) {
			console.error('Failed to fetch visited adventures');
			return redirect(302, '/login');
		} else {
			let res = await initialFetch.json();
			let visited = res.results as Adventure[];

			count = res.count;
			adventures = [...adventures, ...visited];
		}

		return {
			props: {
				adventures,
				count
			}
		};
	}
}) satisfies PageServerLoad;

export const actions: Actions = {
	create: async (event) => {
		const formData = await event.request.formData();

		const type = formData.get('type') as string;
		const name = formData.get('name') as string;
		const location = formData.get('location') as string | null;
		let date = (formData.get('date') as string | null) ?? null;
		const description = formData.get('description') as string | null;
		const activity_types = formData.get('activity_types')
			? (formData.get('activity_types') as string).split(',')
			: null;
		const rating = formData.get('rating') ? Number(formData.get('rating')) : null;
		let link = formData.get('link') as string | null;
		let latitude = formData.get('latitude') as string | null;
		let longitude = formData.get('longitude') as string | null;
		let collection = formData.get('collection') as string | null;

		// check if latitude and longitude are valid
		if (latitude && longitude) {
			if (isNaN(Number(latitude)) || isNaN(Number(longitude))) {
				return {
					status: 400,
					body: { error: 'Invalid latitude or longitude' }
				};
			}
		}

		// round latitude and longitude to 6 decimal places
		if (latitude) {
			latitude = Number(latitude).toFixed(6);
		}
		if (longitude) {
			longitude = Number(longitude).toFixed(6);
		}

		const image = formData.get('image') as File;

		if (!type || !name) {
			return {
				status: 400,
				body: { error: 'Missing required fields' }
			};
		}

		if (date == null || date == '') {
			date = null;
		}

		if (link) {
			link = checkLink(link);
		}

		const formDataToSend = new FormData();
		formDataToSend.append('type', type);
		formDataToSend.append('name', name);
		formDataToSend.append('location', location || '');
		formDataToSend.append('date', date || '');
		formDataToSend.append('description', description || '');
		formDataToSend.append('latitude', latitude || '');
		formDataToSend.append('longitude', longitude || '');

		if (!isNaN(Number(collection))) {
			if (collection !== null) {
				formDataToSend.append('collection', collection);
			}
		}

		if (activity_types) {
			// Filter out empty and duplicate activity types, then trim each activity type
			const cleanedActivityTypes = Array.from(
				new Set(
					activity_types
						.map((activity_type) => activity_type.trim())
						.filter((activity_type) => activity_type !== '' && activity_type !== ',')
				)
			);

			// Append each cleaned activity type to formDataToSend
			cleanedActivityTypes.forEach((activity_type) => {
				formDataToSend.append('activity_types', activity_type);
			});
		}
		formDataToSend.append('rating', rating ? rating.toString() : '');
		formDataToSend.append('link', link || '');
		formDataToSend.append('image', image);

		// log each key-value pair in the FormData
		for (let pair of formDataToSend.entries()) {
			console.log(pair[0] + ', ' + pair[1]);
		}

		let auth = event.cookies.get('auth');

		if (!auth) {
			const refresh = event.cookies.get('refresh');
			if (!refresh) {
				return {
					status: 401,
					body: { message: 'Unauthorized' }
				};
			}
			let res = await tryRefreshToken(refresh);
			if (res) {
				auth = res;
				event.cookies.set('auth', auth, {
					httpOnly: true,
					sameSite: 'lax',
					expires: new Date(Date.now() + 60 * 60 * 1000), // 60 minutes
					path: '/'
				});
			} else {
				return {
					status: 401,
					body: { message: 'Unauthorized' }
				};
			}
		}

		if (!auth) {
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

		const res = await fetch(`${serverEndpoint}/api/adventures/`, {
			method: 'POST',
			headers: {
				'X-CSRFToken': csrfToken,
				Cookie: auth
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
		let image_url = new_id.image;
		let link_url = new_id.link;

		return { id, user_id, image_url, link };
	},
	edit: async (event) => {
		const formData = await event.request.formData();

		const adventureId = formData.get('adventureId') as string;
		const type = formData.get('type') as string;
		const name = formData.get('name') as string;
		const location = formData.get('location') as string | null;
		let date = (formData.get('date') as string | null) ?? null;
		const description = formData.get('description') as string | null;
		let activity_types = formData.get('activity_types')
			? (formData.get('activity_types') as string).split(',')
			: null;
		const rating = formData.get('rating') ? Number(formData.get('rating')) : null;
		let link = formData.get('link') as string | null;
		let latitude = formData.get('latitude') as string | null;
		let longitude = formData.get('longitude') as string | null;
		let is_public = formData.get('is_public') as string | null | boolean;

		if (is_public) {
			is_public = true;
		} else {
			is_public = false;
		}

		// check if latitude and longitude are valid
		if (latitude && longitude) {
			if (isNaN(Number(latitude)) || isNaN(Number(longitude))) {
				return {
					status: 400,
					body: { error: 'Invalid latitude or longitude' }
				};
			}
		}

		// round latitude and longitude to 6 decimal places
		if (latitude) {
			latitude = Number(latitude).toFixed(6);
		}
		if (longitude) {
			longitude = Number(longitude).toFixed(6);
		}

		const image = formData.get('image') as File;

		// console.log(activity_types);

		if (!type || !name) {
			return {
				status: 400,
				body: { error: 'Missing required fields' }
			};
		}

		if (date == null || date == '') {
			date = null;
		}

		if (link) {
			link = checkLink(link);
		}

		const formDataToSend = new FormData();
		formDataToSend.append('type', type);
		formDataToSend.append('name', name);
		formDataToSend.append('location', location || '');
		formDataToSend.append('date', date || '');
		formDataToSend.append('description', description || '');
		formDataToSend.append('latitude', latitude || '');
		formDataToSend.append('longitude', longitude || '');
		formDataToSend.append('is_public', is_public.toString());

		let csrfToken = await fetchCSRFToken();

		if (activity_types) {
			// Filter out empty and duplicate activity types, then trim each activity type
			const cleanedActivityTypes = Array.from(
				new Set(
					activity_types
						.map((activity_type) => activity_type.trim())
						.filter((activity_type) => activity_type !== '' && activity_type !== ',')
				)
			);

			// Append each cleaned activity type to formDataToSend
			cleanedActivityTypes.forEach((activity_type) => {
				formDataToSend.append('activity_types', activity_type);
			});
		} else {
			let res = await fetch(`${serverEndpoint}/api/adventures/${adventureId}/`, {
				method: 'PATCH',
				headers: {
					Cookie: `${event.cookies.get('auth')}`,
					'X-CSRFToken': csrfToken,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ activity_types: [] })
			});
			if (!res.ok) {
				const errorBody = await res.json();
				return {
					status: res.status,
					body: { error: errorBody }
				};
			}
		}
		formDataToSend.append('rating', rating ? rating.toString() : '');
		formDataToSend.append('link', link || '');

		if (image && image.size > 0) {
			formDataToSend.append('image', image);
		}

		let auth = event.cookies.get('auth');

		if (!auth) {
			const refresh = event.cookies.get('refresh');
			if (!refresh) {
				return {
					status: 401,
					body: { message: 'Unauthorized' }
				};
			}
			let res = await tryRefreshToken(refresh);
			if (res) {
				auth = res;
				event.cookies.set('auth', auth, {
					httpOnly: true,
					sameSite: 'lax',
					expires: new Date(Date.now() + 60 * 60 * 1000), // 60 minutes
					path: '/'
				});
			} else {
				return {
					status: 401,
					body: { message: 'Unauthorized' }
				};
			}
		}

		if (!auth) {
			return {
				status: 401,
				body: { message: 'Unauthorized' }
			};
		}

		if (!csrfToken) {
			return {
				status: 500,
				body: { message: 'Failed to fetch CSRF token' }
			};
		}

		const res = await fetch(`${serverEndpoint}/api/adventures/${adventureId}/`, {
			method: 'PATCH',
			headers: {
				'X-CSRFToken': csrfToken,
				Cookie: auth
			},
			body: formDataToSend
		});

		if (!res.ok) {
			const errorBody = await res.json();
			return {
				status: res.status,
				body: { error: errorBody }
			};
		}

		let adventure = await res.json();

		let image_url = adventure.image;
		let link_url = adventure.link;
		return { image_url, link_url };
	}
	// get: async (event) => {
	// 	if (!event.locals.user) {
	// 	}

	// 	const formData = await event.request.formData();
	// 	const visited = formData.get('visited');
	// 	const planned = formData.get('planned');

	// 	let include_collections = formData.get('include_collections') as string;

	// 	if (include_collections) {
	// 		include_collections = 'true';
	// 	} else {
	// 		include_collections = 'false';
	// 	}

	// 	const order_direction = formData.get('order_direction') as string;
	// 	const order_by = formData.get('order_by') as string;

	// 	console.log(order_direction, order_by);

	// 	let adventures: Adventure[] = [];

	// 	if (!event.locals.user) {
	// 		return {
	// 			status: 401,
	// 			body: { message: 'Unauthorized' }
	// 		};
	// 	}

	// 	let filterString = '';
	// 	if (visited) {
	// 		filterString += 'visited';
	// 	}
	// 	if (planned) {
	// 		if (filterString) {
	// 			filterString += ',';
	// 		}
	// 		filterString += 'planned';
	// 	}
	// 	if (!filterString) {
	// 		filterString = '';
	// 	}

	// 	let next = null;
	// 	let previous = null;
	// 	let count = 0;

	// 	console.log(filterString);

	// 	let visitedFetch = await fetch(
	// 		`${serverEndpoint}/api/adventures/filtered?types=${filterString}&order_by=${order_by}&order_direction=${order_direction}&include_collections=${include_collections}`,
	// 		{
	// 			headers: {
	// 				Cookie: `${event.cookies.get('auth')}`
	// 			}
	// 		}
	// 	);
	// 	if (!visitedFetch.ok) {
	// 		console.error('Failed to fetch visited adventures');
	// 		return redirect(302, '/login');
	// 	} else {
	// 		let res = await visitedFetch.json();
	// 		let visited = res.results as Adventure[];
	// 		next = res.next;
	// 		previous = res.previous;
	// 		count = res.count;
	// 		adventures = [...adventures, ...visited];
	// 		console.log(next, previous, count);
	// 	}

	// 	return {
	// 		adventures,
	// 		next,
	// 		previous,
	// 		count
	// 	};
	// },
	// changePage: async (event) => {
	// 	const formData = await event.request.formData();
	// 	const next = formData.get('next') as string;
	// 	const previous = formData.get('previous') as string;
	// 	const page = formData.get('page') as string;

	// 	if (!event.locals.user) {
	// 		return {
	// 			status: 401,
	// 			body: { message: 'Unauthorized' }
	// 		};
	// 	}

	// 	if (!page) {
	// 		return {
	// 			status: 400,
	// 			body: { error: 'Missing required fields' }
	// 		};
	// 	}

	// 	// Start with the provided URL or default to the filtered adventures endpoint
	// 	let url: string = next || previous || '/api/adventures/filtered';

	// 	// Extract the path starting from '/api/adventures'
	// 	const apiIndex = url.indexOf('/api/adventures');
	// 	if (apiIndex !== -1) {
	// 		url = url.slice(apiIndex);
	// 	} else {
	// 		url = '/api/adventures/filtered';
	// 	}

	// 	// Replace or add the page number in the URL
	// 	if (url.includes('page=')) {
	// 		url = url.replace(/page=\d+/, `page=${page}`);
	// 	} else {
	// 		// If 'page=' is not in the URL, add it
	// 		url += url.includes('?') ? '&' : '?';
	// 		url += `page=${page}`;
	// 	}

	// 	const fullUrl = `${serverEndpoint}${url}`;
	// 	console.log(fullUrl);
	// 	console.log(serverEndpoint);

	// 	try {
	// 		const response = await fetch(fullUrl, {
	// 			headers: {
	// 				'Content-Type': 'application/json',
	// 				Cookie: `${event.cookies.get('auth')}`
	// 			}
	// 		});

	// 		if (!response.ok) {
	// 			throw new Error(`HTTP error! status: ${response.status}`);
	// 		}
	// 		const data = await response.json();
	// 		let adventures = data.results as Adventure[];
	// 		let next = data.next;
	// 		let previous = data.previous;
	// 		let count = data.count;

	// 		return {
	// 			status: 200,
	// 			body: {
	// 				adventures,
	// 				next,
	// 				previous,
	// 				count,
	// 				page
	// 			}
	// 		};
	// 	} catch (error) {
	// 		console.error('Error fetching data:', error);
	// 		return {
	// 			status: 500,
	// 			body: { error: 'Failed to fetch data' }
	// 		};
	// 	}
	// },
	// all: async (event) => {
	// 	if (!event.locals.user) {
	// 		return {
	// 			status: 401,
	// 			body: { message: 'Unauthorized' }
	// 		};
	// 	}

	// 	const formData = await event.request.formData();

	// 	let include_collections = formData.get('include_collections') as string;

	// 	if (include_collections !== 'true' && include_collections !== 'false') {
	// 		include_collections = 'false';
	// 	}

	// 	let adventures: Adventure[] = [];

	// 	let visitedFetch = await fetch(
	// 		`${serverEndpoint}/api/adventures/all/?include_collections=${include_collections}`,
	// 		{
	// 			headers: {
	// 				Cookie: `${event.cookies.get('auth')}`,
	// 				'Content-Type': 'application/json'
	// 			}
	// 		}
	// 	);
	// 	if (!visitedFetch.ok) {
	// 		console.error('Failed to fetch all adventures');
	// 		return redirect(302, '/login');
	// 	} else {
	// 		console.log('Fetched all adventures');
	// 		let res = await visitedFetch.json();
	// 		console.log(res);
	// 		adventures = res as Adventure[];
	// 	}

	// 	return {
	// 		adventures
	// 	};
	// }
};
