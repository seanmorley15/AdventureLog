export type CalendarEventType =
	| 'visit'
	| 'transportation'
	| 'lodging'
	| 'collection'
	| 'note'
	| 'checklist'
	| 'location';

export type CalendarTimezoneMode = 'event' | 'local';

export type CalendarApiEvent = {
	id: string;
	type: CalendarEventType;
	title: string;
	start: string;
	end: string;
	all_day: boolean;
	timezone: string | null;
	color: string;
	icon: string;
	category: string;
	location_label: string;
	description: string;
	url: string;
	resource_id: string;
	collection_id: string | null;
	collection_name: string | null;
};

export type CalendarExtendedProps = {
	type: CalendarEventType;
	adventureId?: string;
	adventureName: string;
	category: string;
	icon: string;
	timezone: string;
	timezoneUsed?: string;
	timezoneLabel?: string;
	timezoneMode?: CalendarTimezoneMode;
	isAllDay: boolean;
	formattedStart: string;
	formattedEnd: string;
	location?: string;
	description?: string;
	route?: string;
	checkoutDate?: string | null;
	url?: string;
	resourceId?: string;
	collectionId?: string | null;
	collectionName?: string | null;
};

export type CalendarDisplayEvent = {
	id: string;
	start: string;
	end: string;
	title: string;
	backgroundColor?: string;
	borderColor?: string;
	extendedProps: CalendarExtendedProps;
};

export type CalendarEventFilters = {
	search: string;
	types: Set<CalendarEventType>;
};

export type CalendarStats = {
	total: number;
	byType: Record<CalendarEventType, number>;
	upcoming: number;
	thisMonth: number;
};

export type CalendarViewMode = 'dayGridMonth' | 'timeGridWeek' | 'timeGridDay' | 'agenda';
