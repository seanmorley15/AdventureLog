import type { PageServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

function formatDate(date: Date): string {
	return date.toISOString().split('T')[0];
}

function getInitialRange() {
	const now = new Date();
	const start = new Date(now.getFullYear(), now.getMonth() - 2, 1);
	const end = new Date(now.getFullYear(), now.getMonth() + 5, 0);
	return { start: formatDate(start), end: formatDate(end) };
}

export const load = (async (event) => {
	const sessionId = event.cookies.get('sessionid');
	if (!sessionId) {
		return redirect(302, '/login');
	}

	const { start, end } = getInitialRange();

	const response = await fetch(`${endpoint}/api/calendar/events/?start=${start}&end=${end}`, {
		headers: { Cookie: `sessionid=${sessionId}` }
	});

	let initialEvents: unknown[] = [];
	if (response.ok) {
		const payload = await response.json();
		initialEvents = payload.events || [];
	}

	return {
		props: {
			initialEvents,
			loadError: response.ok ? null : 'calendar.load_error'
		}
	};
}) satisfies PageServerLoad;
