import type { RequestHandler } from './$types';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const GET: RequestHandler = async (event) => {
	try {
		const key = event.params.key;

		// Forward the session ID from cookies
		const sessionid = event.cookies.get('sessionid');
		if (!sessionid) {
			return new Response(JSON.stringify({ error: 'Session ID is missing' }), {
				status: 401,
				headers: { 'Content-Type': 'application/json' }
			});
		}

		let integrationFetch = await fetch(`${endpoint}/api/integrations/immich`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Cookie: `sessionid=${sessionid}`
			}
		});
		if (!integrationFetch.ok) {
			return new Response(JSON.stringify({ error: 'Failed to fetch integration data' }), {
				status: integrationFetch.status,
				headers: { 'Content-Type': 'application/json' }
			});
		}
		const integrationData = await integrationFetch.json();
		const integrationId = integrationData.id;

		// Proxy the request to the backend{
		const res = await fetch(`${endpoint}/api/integrations/immich/${integrationId}/get/${key}`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Cookie: `sessionid=${sessionid}`
			}
		});

		if (!res.ok) {
			// Return an error response if the backend request fails
			const errorData = await res.json();
			return new Response(JSON.stringify(errorData), {
				status: res.status,
				headers: { 'Content-Type': 'application/json' }
			});
		}

		// Get the image as a Blob
		const image = await res.blob();

		// Create a Response to pass the image back
		return new Response(image, {
			status: res.status,
			headers: {
				'Content-Type': res.headers.get('Content-Type') || 'image/jpeg'
			}
		});
	} catch (error) {
		console.error('Error proxying request:', error);
		return new Response(JSON.stringify({ error: 'Failed to fetch image' }), {
			status: 500,
			headers: { 'Content-Type': 'application/json' }
		});
	}
};
