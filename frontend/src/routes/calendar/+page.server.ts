import type { Adventure } from '$lib/types';
import type { PageServerLoad } from './$types';
const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	let sessionId = event.cookies.get('sessionid');
	let visitedFetch = await fetch(`${endpoint}/api/adventures/all/?include_collections=true`, {
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	let adventures = (await visitedFetch.json()) as Adventure[];

	let dates: Array<{
		id: string;
		start: string;
		end: string;
		title: string;
		backgroundColor?: string;
	}> = [];
	adventures.forEach((adventure) => {
		adventure.visits.forEach((visit) => {
			dates.push({
				id: adventure.id,
				start: visit.start_date,
				end: visit.end_date || visit.start_date,
				title: adventure.name + (adventure.category?.icon ? ' ' + adventure.category.icon : '')
			});
		});
	});

	return {
		props: {
			adventures,
			dates
		}
	};
}) satisfies PageServerLoad;
