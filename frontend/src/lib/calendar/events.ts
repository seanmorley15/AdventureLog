import type {
	CalendarApiEvent,
	CalendarDisplayEvent,
	CalendarEventFilters,
	CalendarEventType,
	CalendarStats,
	CalendarTimezoneMode
} from './types';
import { formatAllDayDate } from '$lib/dateUtils';
import { isAllDay } from '$lib';
// @ts-ignore luxon types are not bundled in this project
import { DateTime } from 'luxon';
import type { Collection, Lodging, Transportation } from '$lib/types';

export const CALENDAR_EVENT_COLORS: Record<CalendarEventType, string> = {
	visit: '#3b82f6',
	location: '#3b82f6',
	transportation: '#f97316',
	lodging: '#8b5cf6',
	collection: '#10b981',
	note: '#6366f1',
	checklist: '#14b8a6'
};

export const CALENDAR_EVENT_TYPES: CalendarEventType[] = [
	'visit',
	'transportation',
	'lodging',
	'collection',
	'note',
	'checklist'
];

export function getTransportIcon(type?: string | null): string {
	const normalized = (type || '').toLowerCase();
	if (normalized.includes('flight') || normalized.includes('plane') || normalized.includes('air'))
		return '✈️';
	if (normalized.includes('train') || normalized.includes('rail')) return '🚆';
	if (normalized.includes('bus')) return '🚌';
	if (normalized.includes('car') || normalized.includes('drive')) return '🚗';
	if (normalized.includes('boat') || normalized.includes('ferry') || normalized.includes('ship'))
		return '🚢';
	return '🛣️';
}

export function getLodgingCalendarEndDate(stay: Lodging): string | null {
	const { check_in, check_out } = stay;
	if (!check_out) return check_in || null;
	if (!check_in) return check_out;

	const checkInDate = new Date(check_in.split('T')[0]);
	const checkOutDate = new Date(check_out.split('T')[0]);
	if (Number.isNaN(checkInDate.getTime()) || Number.isNaN(checkOutDate.getTime())) {
		return check_out;
	}
	if (checkOutDate <= checkInDate) return check_out;

	checkOutDate.setDate(checkOutDate.getDate() - 1);
	return checkOutDate.toISOString().split('T')[0];
}

export function buildEventTimes({
	start,
	end,
	timezone,
	mode,
	allDay,
	userTimezone,
	timezoneLabelEvent,
	timezoneLabelLocal
}: {
	start: string | null;
	end: string | null;
	timezone: string | null | undefined;
	mode: CalendarTimezoneMode;
	allDay: boolean;
	userTimezone: string;
	timezoneLabelEvent: string;
	timezoneLabelLocal: string;
}) {
	if (!start) return null;

	const eventTimezone = timezone || userTimezone;
	const targetTimezone = mode === 'local' ? userTimezone : eventTimezone;

	if (allDay) {
		const startDate = start.split('T')[0];
		const endDate = (end || start).split('T')[0];
		const endDateObj = new Date(endDate);
		endDateObj.setDate(endDateObj.getDate() + 1);

		return {
			start: startDate,
			end: endDateObj.toISOString().split('T')[0],
			formattedStart: formatAllDayDate(start),
			formattedEnd: formatAllDayDate(end || start),
			timezoneUsed: targetTimezone,
			timezoneLabel:
				mode === 'local'
					? `${timezoneLabelLocal} (${userTimezone})`
					: `${timezoneLabelEvent} (${eventTimezone})`,
			isAllDay: true
		};
	}

	const startDateTime = DateTime.fromISO(start, { zone: eventTimezone });
	const endDateTime = DateTime.fromISO(end || start, { zone: eventTimezone });
	if (!startDateTime.isValid || !endDateTime.isValid) return null;

	const startConverted = startDateTime.setZone(targetTimezone);
	const endConverted = endDateTime.setZone(targetTimezone);

	return {
		start: startConverted.toISO() || start,
		end: endConverted.toISO() || end || start,
		formattedStart: startConverted.toFormat('ccc, LLL d • t ZZZZ'),
		formattedEnd: endConverted.toFormat('ccc, LLL d • t ZZZZ'),
		timezoneUsed: targetTimezone,
		timezoneLabel:
			mode === 'local'
				? `${timezoneLabelLocal} (${userTimezone})`
				: `${timezoneLabelEvent} (${eventTimezone})`,
		isAllDay: false
	};
}

export function apiEventToDisplayEvent(
	event: CalendarApiEvent,
	mode: CalendarTimezoneMode,
	userTimezone: string,
	labels: { eventTimezone: string; localTimezone: string }
): CalendarDisplayEvent | null {
	const normalizedType = event.type === 'location' ? 'visit' : event.type;
	const allDay = event.all_day || isAllDay(event.start);
	const times = buildEventTimes({
		start: event.start,
		end: event.end,
		timezone: event.timezone,
		mode,
		allDay,
		userTimezone,
		timezoneLabelEvent: labels.eventTimezone,
		timezoneLabelLocal: labels.localTimezone
	});
	if (!times) return null;

	const title = `${event.icon} ${event.title}`.trim();

	return {
		id: event.id,
		start: times.start,
		end: times.end,
		title,
		backgroundColor: event.color || CALENDAR_EVENT_COLORS[normalizedType],
		borderColor: event.color || CALENDAR_EVENT_COLORS[normalizedType],
		extendedProps: {
			type: normalizedType,
			adventureId: normalizedType === 'visit' ? event.resource_id : undefined,
			adventureName: event.title,
			category: event.category,
			icon: event.icon,
			timezone: event.timezone || userTimezone,
			timezoneUsed: times.timezoneUsed,
			timezoneLabel: times.timezoneLabel,
			timezoneMode: mode,
			isAllDay: times.isAllDay,
			formattedStart: times.formattedStart,
			formattedEnd: times.formattedEnd,
			location: event.location_label,
			description: event.description,
			url: event.url,
			resourceId: event.resource_id,
			collectionId: event.collection_id,
			collectionName: event.collection_name
		}
	};
}

export function apiEventsToDisplayEvents(
	events: CalendarApiEvent[],
	mode: CalendarTimezoneMode,
	userTimezone: string,
	labels: { eventTimezone: string; localTimezone: string }
): CalendarDisplayEvent[] {
	return events
		.map((event) => apiEventToDisplayEvent(event, mode, userTimezone, labels))
		.filter((event): event is CalendarDisplayEvent => event !== null);
}

export function filterCalendarEvents(
	events: CalendarDisplayEvent[],
	filters: CalendarEventFilters
): CalendarDisplayEvent[] {
	const query = filters.search.trim().toLowerCase();
	return events.filter((event) => {
		if (!filters.types.has(event.extendedProps.type)) return false;
		if (!query) return true;
		const props = event.extendedProps;
		return (
			props.adventureName.toLowerCase().includes(query) ||
			(props.location || '').toLowerCase().includes(query) ||
			(props.category || '').toLowerCase().includes(query) ||
			(props.collectionName || '').toLowerCase().includes(query) ||
			(props.description || '').toLowerCase().includes(query)
		);
	});
}

export function computeCalendarStats(events: CalendarDisplayEvent[]): CalendarStats {
	const now = DateTime.now();
	const monthStart = now.startOf('month');
	const monthEnd = now.endOf('month');

	const byType = CALENDAR_EVENT_TYPES.reduce(
		(acc, type) => {
			acc[type] = 0;
			return acc;
		},
		{} as Record<CalendarEventType, number>
	);

	let upcoming = 0;
	let thisMonth = 0;

	for (const event of events) {
		const type = event.extendedProps.type;
		byType[type] = (byType[type] || 0) + 1;

		const start = DateTime.fromISO(event.start);
		if (!start.isValid) continue;
		if (start >= now.startOf('day')) upcoming += 1;
		if (start >= monthStart && start <= monthEnd) thisMonth += 1;
	}

	return {
		total: events.length,
		byType,
		upcoming,
		thisMonth
	};
}

export function groupEventsByDay(events: CalendarDisplayEvent[]): Array<{
	date: string;
	label: string;
	events: CalendarDisplayEvent[];
}> {
	const groups = new Map<string, CalendarDisplayEvent[]>();

	for (const event of events) {
		const dayKey = event.start.split('T')[0];
		const existing = groups.get(dayKey) || [];
		existing.push(event);
		groups.set(dayKey, existing);
	}

	return [...groups.entries()]
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([date, dayEvents]) => ({
			date,
			label: DateTime.fromISO(date).toFormat('cccc, LLL d, yyyy'),
			events: dayEvents.sort((a, b) => a.start.localeCompare(b.start))
		}));
}

export function buildCollectionCalendarEvents(
	collection: Collection,
	mode: CalendarTimezoneMode,
	userTimezone: string,
	labels: { eventTimezone: string; localTimezone: string },
	translate: (key: string) => string
): CalendarDisplayEvent[] {
	const events: CalendarDisplayEvent[] = [];

	(collection.locations || []).forEach((loc) => {
		(loc.visits || []).forEach((visit) => {
			if (!visit.start_date) return;
			const times = buildEventTimes({
				start: visit.start_date,
				end: visit.end_date || visit.start_date,
				timezone: visit.timezone,
				mode,
				allDay: isAllDay(visit.start_date),
				userTimezone,
				timezoneLabelEvent: labels.eventTimezone,
				timezoneLabelLocal: labels.localTimezone
			});
			if (!times) return;

			events.push({
				id: `location-${loc.id}-${visit.id}`,
				title: `${loc.category?.icon || '📍'} ${loc.name}`,
				start: times.start,
				end: times.end,
				backgroundColor: CALENDAR_EVENT_COLORS.visit,
				borderColor: CALENDAR_EVENT_COLORS.visit,
				extendedProps: {
					type: 'visit',
					adventureId: loc.id,
					adventureName: loc.name,
					category: loc.category?.display_name || loc.category?.name || 'Adventure',
					icon: loc.category?.icon || '🗺️',
					timezone: visit.timezone || userTimezone,
					timezoneUsed: times.timezoneUsed,
					timezoneLabel: times.timezoneLabel,
					timezoneMode: mode,
					isAllDay: times.isAllDay,
					formattedStart: times.formattedStart,
					formattedEnd: times.formattedEnd,
					location: loc.location || '',
					description: loc.description || '',
					url: `/locations/${loc.id}`,
					resourceId: loc.id,
					collectionId: collection.id,
					collectionName: collection.name
				}
			});
		});
	});

	(collection.transportations || []).forEach((transportation: Transportation) => {
		if (!transportation.date) return;
		const times = buildEventTimes({
			start: transportation.date,
			end: transportation.end_date || transportation.date,
			timezone: transportation.start_timezone || transportation.end_timezone,
			mode,
			allDay: isAllDay(transportation.date),
			userTimezone,
			timezoneLabelEvent: labels.eventTimezone,
			timezoneLabelLocal: labels.localTimezone
		});
		if (!times) return;

		const route = [transportation.from_location, transportation.to_location]
			.filter(Boolean)
			.join(' → ');

		events.push({
			id: `transport-${transportation.id}`,
			title: `${getTransportIcon(transportation.type)} ${
				transportation.name || transportation.type || translate('adventures.transportation')
			}`,
			start: times.start,
			end: times.end,
			backgroundColor: CALENDAR_EVENT_COLORS.transportation,
			borderColor: CALENDAR_EVENT_COLORS.transportation,
			extendedProps: {
				type: 'transportation',
				adventureName: transportation.name || transportation.type || 'Transportation',
				category: transportation.type || 'Transportation',
				icon: getTransportIcon(transportation.type),
				timezone: transportation.start_timezone || transportation.end_timezone || userTimezone,
				timezoneUsed: times.timezoneUsed,
				timezoneLabel: times.timezoneLabel,
				timezoneMode: mode,
				isAllDay: times.isAllDay,
				formattedStart: times.formattedStart,
				formattedEnd: times.formattedEnd,
				location: route || transportation.description || '',
				description: transportation.description || '',
				route,
				url: `/transportations/${transportation.id}`,
				resourceId: transportation.id,
				collectionId: collection.id,
				collectionName: collection.name
			}
		});
	});

	(collection.lodging || []).forEach((stay: Lodging) => {
		const start = stay.check_in || stay.check_out;
		if (!start) return;
		const calendarEnd = getLodgingCalendarEndDate(stay);
		const times = buildEventTimes({
			start,
			end: calendarEnd || start,
			timezone: stay.timezone,
			mode,
			allDay: true,
			userTimezone,
			timezoneLabelEvent: labels.eventTimezone,
			timezoneLabelLocal: labels.localTimezone
		});
		if (!times) return;

		events.push({
			id: `lodging-${stay.id}`,
			title: `🏨 ${stay.name}`,
			start: times.start,
			end: times.end,
			backgroundColor: CALENDAR_EVENT_COLORS.lodging,
			borderColor: CALENDAR_EVENT_COLORS.lodging,
			extendedProps: {
				type: 'lodging',
				adventureName: stay.name,
				category: stay.type || 'Lodging',
				icon: '🏨',
				timezone: stay.timezone || userTimezone,
				timezoneUsed: times.timezoneUsed,
				timezoneLabel: times.timezoneLabel,
				timezoneMode: mode,
				isAllDay: true,
				formattedStart: times.formattedStart,
				formattedEnd: times.formattedEnd,
				checkoutDate: stay.check_out || null,
				location: stay.location || '',
				description: stay.description || '',
				url: `/lodging/${stay.id}`,
				resourceId: stay.id,
				collectionId: collection.id,
				collectionName: collection.name
			}
		});
	});

	return events.sort((a, b) => a.start.localeCompare(b.start));
}

export function formatCalendarRange(start: Date, end: Date): { start: string; end: string } {
	const startDt = DateTime.fromJSDate(start).startOf('day');
	const endDt = DateTime.fromJSDate(end).endOf('day');
	return {
		start: startDt.toISODate() || '',
		end: endDt.toISODate() || ''
	};
}
