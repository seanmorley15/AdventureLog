import { json } from '@sveltejs/kit';
import type { RequestHandler } from '../data/$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const POST: RequestHandler = async (event) => {
	let allActivities: string[] = [];
	let res = await fetch(`${endpoint}/api/activity-types/types/`, {
		headers: {
			'Content-Type': 'application/json',
			Cookie: `${event.cookies.get('auth')}`
		}
	});
	let data = await res.json();
	if (data) {
		allActivities = data;
	}
	return json({ activities: allActivities });
};
