import type { Location } from '$lib/types';
import type { PageServerLoad } from './$types';
import { formatDateInTimezone, formatAllDayDate } from '$lib/dateUtils';
import { isAllDay } from '$lib';

const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const load = (async (event) => {
	let sessionId = event.cookies.get('sessionid');
	let visitedFetch = await fetch(
		`${endpoint}/api/locations/all?include_collections=true&nested=true&allowed_nested_fields=visits`,
		{
			headers: {
				Cookie: `sessionid=${sessionId}`
			}
		}
	);
	let adventures = (await visitedFetch.json()) as Location[];

	// Get user's local timezone as fallback
	const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

	let dates: Array<{
		id: string;
		start: string;
		end: string;
		title: string;
		backgroundColor?: string;
		extendedProps?: {
			adventureName: string;
			category: string;
			icon: string;
			timezone: string;
			isAllDay: boolean;
			formattedStart: string;
			formattedEnd: string;
			location?: string;
			description?: string;
			adventureId?: string;
		};
	}> = [];

	adventures.forEach((adventure) => {
		adventure.visits.forEach((visit) => {
			if (visit.start_date) {
				let startDate = visit.start_date;
				let endDate = visit.end_date || visit.start_date;
				const targetTimezone = visit.timezone || userTimezone;
				const allDay = isAllDay(visit.start_date);

				// Handle timezone conversion for non-all-day events
				if (!allDay) {
					// Convert UTC dates to target timezone
					const startDateTime = new Date(visit.start_date);
					const endDateTime = new Date(visit.end_date || visit.start_date);

					// Format for calendar (ISO string in target timezone)
					startDate = new Intl.DateTimeFormat('sv-SE', {
						timeZone: targetTimezone,
						year: 'numeric',
						month: '2-digit',
						day: '2-digit',
						hour: '2-digit',
						minute: '2-digit',
						hourCycle: 'h23'
					})
						.format(startDateTime)
						.replace(' ', 'T');

					endDate = new Intl.DateTimeFormat('sv-SE', {
						timeZone: targetTimezone,
						year: 'numeric',
						month: '2-digit',
						day: '2-digit',
						hour: '2-digit',
						minute: '2-digit',
						hourCycle: 'h23'
					})
						.format(endDateTime)
						.replace(' ', 'T');
				} else {
					// For all-day events, use just the date part
					startDate = visit.start_date.split('T')[0];

					// For all-day events, add one day to end date to make it inclusive
					const endDateObj = new Date(visit.end_date || visit.start_date);
					endDateObj.setDate(endDateObj.getDate() + 1);
					endDate = endDateObj.toISOString().split('T')[0];
				}

				// Create detailed title with timezone info
				let detailedTitle = adventure.name;
				if (adventure.category?.icon) {
					detailedTitle = `${adventure.category.icon} ${detailedTitle}`;
				}

				// Add time info to title for non-all-day events
				if (!allDay) {
					const startTime = formatDateInTimezone(visit.start_date, targetTimezone);
					detailedTitle += ` (${startTime.split(' ').slice(-2).join(' ')})`;
					if (targetTimezone !== userTimezone) {
						detailedTitle += ` ${targetTimezone}`;
					}
				}

				dates.push({
					id: adventure.id,
					start: startDate,
					end: endDate,
					title: detailedTitle,
					backgroundColor: '#3b82f6',
					extendedProps: {
						adventureName: adventure.name,
						category: adventure.category?.name || 'Adventure',
						icon: adventure.category?.icon || '🗺️',
						timezone: targetTimezone,
						isAllDay: allDay,
						formattedStart: allDay
							? formatAllDayDate(visit.start_date)
							: formatDateInTimezone(visit.start_date, targetTimezone),
						formattedEnd: allDay
							? formatAllDayDate(visit.end_date || visit.start_date)
							: formatDateInTimezone(visit.end_date || visit.start_date, targetTimezone),
						location: adventure.location || '',
						description: adventure.description || '',
						adventureId: adventure.id
					}
				});
			}
		});
	});

	let icsFetch = await fetch(`${endpoint}/api/ics-calendar/generate`, {
		headers: {
			Cookie: `sessionid=${sessionId}`
		}
	});
	let ics_calendar = await icsFetch.text();

	return {
		props: {
			adventures,
			dates,
			ics_calendar
		}
	};
}) satisfies PageServerLoad;
