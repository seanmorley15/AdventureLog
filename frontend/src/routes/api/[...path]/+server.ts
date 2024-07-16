const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
import { json } from '@sveltejs/kit';

/** @type {import('./$types').RequestHandler} */
export async function GET({ url, params, request, fetch, cookies }) {
	return handleRequest(url, params, request, fetch, cookies);
}

/** @type {import('./$types').RequestHandler} */
export async function POST({ url, params, request, fetch, cookies }) {
	return handleRequest(url, params, request, fetch, cookies);
}

// Implement other HTTP methods as needed (PUT, DELETE, etc.)

async function handleRequest(url: any, params: any, request: any, fetch: any, cookies: any) {
	const path = params.path;
	const targetUrl = `${endpoint}/api/${path}${url.search}&format=json`;

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
