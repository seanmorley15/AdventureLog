import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { DashboardData } from '$lib/types';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

const emptyDashboard: DashboardData = {
	stats: null,
	recent_locations: [],
	upcoming_trips: [],
	active_trip: null,
	upcoming_events: [],
	invite_count: 0
};

export const load = (async (event) => {
	if (!event.locals.user) {
		return redirect(302, '/login');
	}

	let loadError = false;
	let dashboard: DashboardData = { ...emptyDashboard };

	try {
		const res = await event.fetch(`${serverEndpoint}/api/stats/dashboard/`, {
			headers: {
				Cookie: `sessionid=${event.cookies.get('sessionid')}`
			},
			credentials: 'include'
		});

		if (!res.ok) {
			console.error('Failed to fetch dashboard data', res.status);
			loadError = true;
		} else {
			dashboard = await res.json();
		}
	} catch (error) {
		console.error('Error loading dashboard', error);
		loadError = true;
	}

	return {
		props: {
			stats: dashboard.stats,
			recentLocations: dashboard.recent_locations ?? [],
			upcomingTrips: dashboard.upcoming_trips ?? [],
			activeTrip: dashboard.active_trip,
			upcomingEvents: dashboard.upcoming_events ?? [],
			inviteCount: dashboard.invite_count ?? 0,
			loadError
		}
	};
}) satisfies PageServerLoad;
