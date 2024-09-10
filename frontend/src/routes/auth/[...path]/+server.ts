const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
import { json } from '@sveltejs/kit';

/** @type {import('./$types').RequestHandler} */
export async function GET({ url, params, request, fetch, cookies }) {
	// add the param format = json to the url or add additional if anothre param is already present
	if (url.search) {
		url.search = url.search + '&format=json';
	} else {
		url.search = '?format=json';
	}
	return handleRequest(url, params, request, fetch, cookies);
}

/** @type {import('./$types').RequestHandler} */
export async function POST({ url, params, request, fetch, cookies }) {
	return handleRequest(url, params, request, fetch, cookies, true);
}

export async function PATCH({ url, params, request, fetch, cookies }) {
	return handleRequest(url, params, request, fetch, cookies, true);
}

export async function PUT({ url, params, request, fetch, cookies }) {
	return handleRequest(url, params, request, fetch, cookies, true);
}

export async function DELETE({ url, params, request, fetch, cookies }) {
	return handleRequest(url, params, request, fetch, cookies, true);
}

// Implement other HTTP methods as needed (PUT, DELETE, etc.)

async function handleRequest(
	url: any,
	params: any,
	request: any,
	fetch: any,
	cookies: any,
	requreTrailingSlash: boolean | undefined = false
) {
	const path = params.path;
	let targetUrl = `${endpoint}/auth/${path}${url.search}`;

	if (requreTrailingSlash && !targetUrl.endsWith('/')) {
		targetUrl += '/';
	}

	const headers = new Headers(request.headers);

	const authCookie = cookies.get('auth');

	if (authCookie) {
		headers.set('Cookie', `${authCookie}`);
	}

	try {
		const response = await fetch(targetUrl, {
			method: request.method,
			headers: headers,
			body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.text() : undefined
		});

		if (response.status === 204) {
			// For 204 No Content, return a response with no body
			return new Response(null, {
				status: 204,
				headers: response.headers
			});
		}

		const responseData = await response.text();

		return new Response(responseData, {
			status: response.status,
			headers: response.headers
		});
	} catch (error) {
		console.error('Error forwarding request:', error);
		return json({ error: 'Internal Server Error' }, { status: 500 });
	}
}
