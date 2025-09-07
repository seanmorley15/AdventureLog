// @ts-ignore
import { DateTime } from 'luxon';
import type { Checklist, Collection, Lodging, Note, Transportation, Visit } from './types';
import { isAllDay } from '$lib';

/**
 * Convert a UTC ISO date to a datetime-local value in the specified timezone
 */
export function toLocalDatetime(
	utcDate: string | null,
	timezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone
): string {
	if (!utcDate) return '';
	const dt = DateTime.fromISO(utcDate, { zone: 'UTC' });
	if (!dt.isValid) return '';
	const isoString = dt.setZone(timezone).toISO({
		suppressSeconds: true,
		includeOffset: false
	});
	return isoString ? isoString.slice(0, 16) : '';
}

/**
 * Convert a local datetime to UTC
 */
export function toUTCDatetime(
	localDate: string,
	timezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone,
	allDay: boolean = false
): string | null {
	if (!localDate) return null;
	if (allDay) {
		// Treat as date only, set UTC midnight
		return DateTime.fromISO(localDate, { zone: 'UTC' })
			.startOf('day')
			.toISO({ suppressMilliseconds: true });
	}
	return DateTime.fromISO(localDate, { zone: timezone })
		.toUTC()
		.toISO({ suppressMilliseconds: true });
}

/**
 * Updates local datetime values based on UTC date and timezone
 */
export function updateLocalDate({
	utcDate,
	timezone
}: {
	utcDate: string | null;
	timezone: string;
}) {
	return { localDate: toLocalDatetime(utcDate, timezone) };
}

/**
 * Updates UTC datetime values based on local datetime and timezone
 */
export function updateUTCDate({
	localDate,
	timezone,
	allDay = false
}: {
	localDate: string;
	timezone: string;
	allDay?: boolean;
}) {
	return { utcDate: toUTCDatetime(localDate, timezone, allDay) };
}

/**
 * Validate date ranges using UTC comparison
 */
export function validateDateRange(
	startDate: string,
	endDate: string
): { valid: boolean; error?: string } {
	if (endDate && !startDate) {
		return { valid: false, error: 'Start date is required when end date is provided' };
	}
	if (
		startDate &&
		endDate &&
		DateTime.fromISO(startDate, { zone: 'utc' }).toMillis() >
			DateTime.fromISO(endDate, { zone: 'utc' }).toMillis()
	) {
		return { valid: false, error: 'Start date must be before end date (based on UTC)' };
	}
	return { valid: true };
}

export function formatDateInTimezone(utcDate: string, timezone: string | null): string {
	if (!utcDate) return '';
	try {
		return new Intl.DateTimeFormat(undefined, {
			timeZone: timezone || undefined,
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
			hour12: true
		}).format(new Date(utcDate));
	} catch {
		return new Date(utcDate).toLocaleString();
	}
}

export function formatUTCDate(utcDate: string | null): string {
	if (!utcDate) return '';
	const dateTime = DateTime.fromISO(utcDate);
	if (!dateTime.isValid) return '';
	return dateTime.toISO()?.slice(0, 16).replace('T', ' ') || '';
}

export function formatAllDayDate(dateString: string): string {
	if (!dateString) return '';
	const datePart = dateString.split('T')[0];
	const dateWithMidday = `${datePart}T12:00:00`;
	return new Intl.DateTimeFormat('en-US', {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	}).format(new Date(dateWithMidday));
}

// ==== FIXED TIMEZONE-AWARE DATE RANGE LOGIC ====

/**
 * Extracts start and end dates from various entity types (Luxon DateTime)
 * Returns also isAllDay flag for correct comparison logic
 */
function getEntityDateRange(entity: Visit | Transportation | Lodging | Note | Checklist): {
	start: DateTime | null;
	end: DateTime | null;
	isAllDay: boolean;
} {
	let start: DateTime | null = null;
	let end: DateTime | null = null;
	let isAllDayEvent = false;
	try {
		let timezone = (entity as Visit).timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
		if ('start_date' in entity && 'end_date' in entity) {
			// Check if all-day (no time portion)
			isAllDayEvent = isAllDay(entity.start_date) && isAllDay(entity.end_date);
			console;
			if (isAllDayEvent) {
				start = entity.start_date
					? DateTime.fromISO(entity.start_date.split('T')[0], { zone: 'UTC' }).startOf('day')
					: null;
				end = entity.end_date
					? DateTime.fromISO(entity.end_date.split('T')[0], { zone: 'UTC' }).endOf('day')
					: null;
			} else {
				start = DateTime.fromISO(entity.start_date, { zone: 'UTC' }).setZone(timezone);
				end = DateTime.fromISO(entity.end_date, { zone: 'UTC' }).setZone(timezone);
			}
		} else if ('date' in entity && 'end_date' in entity) {
			isAllDayEvent = !!(entity.date && entity.date.length === 10);
			if (isAllDayEvent) {
				start = DateTime.fromISO(entity.date, { zone: 'UTC' }).startOf('day');
				end = DateTime.fromISO(entity.end_date, { zone: 'UTC' }).endOf('day');
			} else {
				start = DateTime.fromISO(entity.date, { zone: 'UTC' }).setZone(timezone);
				end = DateTime.fromISO(entity.end_date, { zone: 'UTC' }).setZone(timezone);
			}
		} else if ('check_in' in entity && 'check_out' in entity) {
			isAllDayEvent = !!(entity.check_in && entity.check_in.length === 10);
			if (isAllDayEvent) {
				start = DateTime.fromISO(entity.check_in, { zone: 'UTC' }).startOf('day');
				end = DateTime.fromISO(entity.check_out, { zone: 'UTC' }).endOf('day');
			} else {
				start = DateTime.fromISO(entity.check_in, { zone: 'UTC' }).setZone(timezone);
				end = DateTime.fromISO(entity.check_out, { zone: 'UTC' }).setZone(timezone);
			}
		} else if ('date' in entity) {
			isAllDayEvent = !!(entity.date && entity.date.length === 10);
			if (isAllDayEvent) {
				start = DateTime.fromISO(entity.date, { zone: 'UTC' }).startOf('day');
				end = start;
			} else {
				start = DateTime.fromISO(entity.date, { zone: 'UTC' }).setZone(timezone);
				end = start;
			}
		}
	} catch (error) {
		console.error('Error processing entity dates:', error);
	}
	return { start, end, isAllDay: isAllDayEvent };
}

/**
 * Extract collection start/end as Luxon DateTime w/allDay logic
 */
function getCollectionDateRange(collection: Collection): {
	start: DateTime | null;
	end: DateTime | null;
	isAllDay: boolean;
} {
	if (!collection.start_date || !collection.end_date) {
		return { start: null, end: null, isAllDay: false };
	}

	// Assume collection always uses full datetimes in ISO string
	const isAllDay = collection.start_date.length === 10 && collection.end_date.length === 10;
	const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	const start = isAllDay
		? DateTime.fromISO(collection.start_date, { zone: 'UTC' }).startOf('day')
		: DateTime.fromISO(collection.start_date, { zone: 'UTC' }).setZone(timezone);
	const end = isAllDay
		? DateTime.fromISO(collection.end_date, { zone: 'UTC' }).endOf('day')
		: DateTime.fromISO(collection.end_date, { zone: 'UTC' }).setZone(timezone);
	return { start, end, isAllDay };
}

/**
 * Checks if an entity falls within a collection's date range (timezone-safe, all-day-aware)
 */
export function isEntityInCollectionDateRange(
	entity: Visit | Transportation | Lodging | Note | Checklist,
	collection: Collection
): boolean {
	if (!collection?.start_date || !collection.end_date) {
		return false;
	}

	const { start: entityStart, end: entityEnd, isAllDay: entityAllDay } = getEntityDateRange(entity);
	const {
		start: collStart,
		end: collEnd,
		isAllDay: collAllDay
	} = getCollectionDateRange(collection);

	// If any dates are missing, don't match
	if (!entityStart || !collStart) return false;

	// If either side is all-day, use date comparison
	if (entityAllDay || collAllDay) {
		// Compare only date components
		const entStartDate = entityStart.startOf('day');
		const entEndDate = (entityEnd || entityStart).endOf('day');
		const colStartDate = collStart.startOf('day');
		const colEndDate = collEnd.endOf('day');
		return entStartDate <= colEndDate && entEndDate >= colStartDate;
	} else {
		// Compare actual DateTimes
		const entEnd = entityEnd || entityStart;
		return entityStart <= collEnd && entEnd >= collStart;
	}
}

export function isEntityOutsideCollectionDateRange(
	entity: Visit | Transportation | Lodging | Note | Checklist,
	collection: Collection
): boolean {
	return !isEntityInCollectionDateRange(entity, collection);
}

export function getEntitiesInDateRange<
	T extends Visit | Transportation | Lodging | Note | Checklist
>(entities: T[], collection: Collection): T[] {
	return entities.filter((entity) => isEntityInCollectionDateRange(entity, collection));
}

export function getEntitiesOutsideDateRange<
	T extends Visit | Transportation | Lodging | Note | Checklist
>(entities: T[], collection: Collection): T[] {
	return entities.filter((entity) => isEntityOutsideCollectionDateRange(entity, collection));
}

export const VALID_TIMEZONES = [
	'Africa/Abidjan',
	'Africa/Accra',
	'Africa/Addis_Ababa',
	'Africa/Algiers',
	'Africa/Asmera',
	'Africa/Bamako',
	'Africa/Bangui',
	'Africa/Banjul',
	'Africa/Bissau',
	'Africa/Blantyre',
	'Africa/Brazzaville',
	'Africa/Bujumbura',
	'Africa/Cairo',
	'Africa/Casablanca',
	'Africa/Ceuta',
	'Africa/Conakry',
	'Africa/Dakar',
	'Africa/Dar_es_Salaam',
	'Africa/Djibouti',
	'Africa/Douala',
	'Africa/El_Aaiun',
	'Africa/Freetown',
	'Africa/Gaborone',
	'Africa/Harare',
	'Africa/Johannesburg',
	'Africa/Juba',
	'Africa/Kampala',
	'Africa/Khartoum',
	'Africa/Kigali',
	'Africa/Kinshasa',
	'Africa/Lagos',
	'Africa/Libreville',
	'Africa/Lome',
	'Africa/Luanda',
	'Africa/Lubumbashi',
	'Africa/Lusaka',
	'Africa/Malabo',
	'Africa/Maputo',
	'Africa/Maseru',
	'Africa/Mbabane',
	'Africa/Mogadishu',
	'Africa/Monrovia',
	'Africa/Nairobi',
	'Africa/Ndjamena',
	'Africa/Niamey',
	'Africa/Nouakchott',
	'Africa/Ouagadougou',
	'Africa/Porto-Novo',
	'Africa/Sao_Tome',
	'Africa/Tripoli',
	'Africa/Tunis',
	'Africa/Windhoek',
	'America/Adak',
	'America/Anchorage',
	'America/Anguilla',
	'America/Antigua',
	'America/Araguaina',
	'America/Argentina/La_Rioja',
	'America/Argentina/Rio_Gallegos',
	'America/Argentina/Salta',
	'America/Argentina/San_Juan',
	'America/Argentina/San_Luis',
	'America/Argentina/Tucuman',
	'America/Argentina/Ushuaia',
	'America/Aruba',
	'America/Asuncion',
	'America/Bahia',
	'America/Bahia_Banderas',
	'America/Barbados',
	'America/Belem',
	'America/Belize',
	'America/Blanc-Sablon',
	'America/Boa_Vista',
	'America/Bogota',
	'America/Boise',
	'America/Buenos_Aires',
	'America/Cambridge_Bay',
	'America/Campo_Grande',
	'America/Cancun',
	'America/Caracas',
	'America/Catamarca',
	'America/Cayenne',
	'America/Cayman',
	'America/Chicago',
	'America/Chihuahua',
	'America/Ciudad_Juarez',
	'America/Coral_Harbour',
	'America/Cordoba',
	'America/Costa_Rica',
	'America/Creston',
	'America/Cuiaba',
	'America/Curacao',
	'America/Danmarkshavn',
	'America/Dawson',
	'America/Dawson_Creek',
	'America/Denver',
	'America/Detroit',
	'America/Dominica',
	'America/Edmonton',
	'America/Eirunepe',
	'America/El_Salvador',
	'America/Fort_Nelson',
	'America/Fortaleza',
	'America/Glace_Bay',
	'America/Godthab',
	'America/Goose_Bay',
	'America/Grand_Turk',
	'America/Grenada',
	'America/Guadeloupe',
	'America/Guatemala',
	'America/Guayaquil',
	'America/Guyana',
	'America/Halifax',
	'America/Havana',
	'America/Hermosillo',
	'America/Indiana/Knox',
	'America/Indiana/Marengo',
	'America/Indiana/Petersburg',
	'America/Indiana/Tell_City',
	'America/Indiana/Vevay',
	'America/Indiana/Vincennes',
	'America/Indiana/Winamac',
	'America/Indianapolis',
	'America/Inuvik',
	'America/Iqaluit',
	'America/Jamaica',
	'America/Jujuy',
	'America/Juneau',
	'America/Kentucky/Monticello',
	'America/Kralendijk',
	'America/La_Paz',
	'America/Lima',
	'America/Los_Angeles',
	'America/Louisville',
	'America/Lower_Princes',
	'America/Maceio',
	'America/Managua',
	'America/Manaus',
	'America/Marigot',
	'America/Martinique',
	'America/Matamoros',
	'America/Mazatlan',
	'America/Mendoza',
	'America/Menominee',
	'America/Merida',
	'America/Metlakatla',
	'America/Mexico_City',
	'America/Miquelon',
	'America/Moncton',
	'America/Monterrey',
	'America/Montevideo',
	'America/Montserrat',
	'America/Nassau',
	'America/New_York',
	'America/Nome',
	'America/Noronha',
	'America/North_Dakota/Beulah',
	'America/North_Dakota/Center',
	'America/North_Dakota/New_Salem',
	'America/Ojinaga',
	'America/Panama',
	'America/Paramaribo',
	'America/Phoenix',
	'America/Port-au-Prince',
	'America/Port_of_Spain',
	'America/Porto_Velho',
	'America/Puerto_Rico',
	'America/Punta_Arenas',
	'America/Rankin_Inlet',
	'America/Recife',
	'America/Regina',
	'America/Resolute',
	'America/Rio_Branco',
	'America/Santarem',
	'America/Santiago',
	'America/Santo_Domingo',
	'America/Sao_Paulo',
	'America/Scoresbysund',
	'America/Sitka',
	'America/St_Barthelemy',
	'America/St_Johns',
	'America/St_Kitts',
	'America/St_Lucia',
	'America/St_Thomas',
	'America/St_Vincent',
	'America/Swift_Current',
	'America/Tegucigalpa',
	'America/Thule',
	'America/Tijuana',
	'America/Toronto',
	'America/Tortola',
	'America/Vancouver',
	'America/Whitehorse',
	'America/Winnipeg',
	'America/Yakutat',
	'Antarctica/Casey',
	'Antarctica/Davis',
	'Antarctica/DumontDUrville',
	'Antarctica/Macquarie',
	'Antarctica/Mawson',
	'Antarctica/McMurdo',
	'Antarctica/Palmer',
	'Antarctica/Rothera',
	'Antarctica/Syowa',
	'Antarctica/Troll',
	'Antarctica/Vostok',
	'Arctic/Longyearbyen',
	'Asia/Aden',
	'Asia/Almaty',
	'Asia/Amman',
	'Asia/Anadyr',
	'Asia/Aqtau',
	'Asia/Aqtobe',
	'Asia/Ashgabat',
	'Asia/Atyrau',
	'Asia/Baghdad',
	'Asia/Bahrain',
	'Asia/Baku',
	'Asia/Bangkok',
	'Asia/Barnaul',
	'Asia/Beirut',
	'Asia/Bishkek',
	'Asia/Brunei',
	'Asia/Calcutta',
	'Asia/Chita',
	'Asia/Colombo',
	'Asia/Damascus',
	'Asia/Dhaka',
	'Asia/Dili',
	'Asia/Dubai',
	'Asia/Dushanbe',
	'Asia/Famagusta',
	'Asia/Gaza',
	'Asia/Hebron',
	'Asia/Hong_Kong',
	'Asia/Hovd',
	'Asia/Irkutsk',
	'Asia/Jakarta',
	'Asia/Jayapura',
	'Asia/Jerusalem',
	'Asia/Kabul',
	'Asia/Kamchatka',
	'Asia/Karachi',
	'Asia/Katmandu',
	'Asia/Khandyga',
	'Asia/Krasnoyarsk',
	'Asia/Kuala_Lumpur',
	'Asia/Kuching',
	'Asia/Kuwait',
	'Asia/Macau',
	'Asia/Magadan',
	'Asia/Makassar',
	'Asia/Manila',
	'Asia/Muscat',
	'Asia/Nicosia',
	'Asia/Novokuznetsk',
	'Asia/Novosibirsk',
	'Asia/Omsk',
	'Asia/Oral',
	'Asia/Phnom_Penh',
	'Asia/Pontianak',
	'Asia/Pyongyang',
	'Asia/Qatar',
	'Asia/Qostanay',
	'Asia/Qyzylorda',
	'Asia/Rangoon',
	'Asia/Riyadh',
	'Asia/Saigon',
	'Asia/Sakhalin',
	'Asia/Samarkand',
	'Asia/Seoul',
	'Asia/Shanghai',
	'Asia/Singapore',
	'Asia/Srednekolymsk',
	'Asia/Taipei',
	'Asia/Tashkent',
	'Asia/Tbilisi',
	'Asia/Tehran',
	'Asia/Thimphu',
	'Asia/Tokyo',
	'Asia/Tomsk',
	'Asia/Ulaanbaatar',
	'Asia/Urumqi',
	'Asia/Ust-Nera',
	'Asia/Vientiane',
	'Asia/Vladivostok',
	'Asia/Yakutsk',
	'Asia/Yekaterinburg',
	'Asia/Yerevan',
	'Atlantic/Azores',
	'Atlantic/Bermuda',
	'Atlantic/Canary',
	'Atlantic/Cape_Verde',
	'Atlantic/Faeroe',
	'Atlantic/Madeira',
	'Atlantic/Reykjavik',
	'Atlantic/South_Georgia',
	'Atlantic/St_Helena',
	'Atlantic/Stanley',
	'Australia/Adelaide',
	'Australia/Brisbane',
	'Australia/Broken_Hill',
	'Australia/Darwin',
	'Australia/Eucla',
	'Australia/Hobart',
	'Australia/Lindeman',
	'Australia/Lord_Howe',
	'Australia/Melbourne',
	'Australia/Perth',
	'Australia/Sydney',
	'Europe/Amsterdam',
	'Europe/Andorra',
	'Europe/Astrakhan',
	'Europe/Athens',
	'Europe/Belgrade',
	'Europe/Berlin',
	'Europe/Bratislava',
	'Europe/Brussels',
	'Europe/Bucharest',
	'Europe/Budapest',
	'Europe/Busingen',
	'Europe/Chisinau',
	'Europe/Copenhagen',
	'Europe/Dublin',
	'Europe/Gibraltar',
	'Europe/Guernsey',
	'Europe/Helsinki',
	'Europe/Isle_of_Man',
	'Europe/Istanbul',
	'Europe/Jersey',
	'Europe/Kaliningrad',
	'Europe/Kiev',
	'Europe/Kirov',
	'Europe/Lisbon',
	'Europe/Ljubljana',
	'Europe/London',
	'Europe/Luxembourg',
	'Europe/Madrid',
	'Europe/Malta',
	'Europe/Mariehamn',
	'Europe/Minsk',
	'Europe/Monaco',
	'Europe/Moscow',
	'Europe/Oslo',
	'Europe/Paris',
	'Europe/Podgorica',
	'Europe/Prague',
	'Europe/Riga',
	'Europe/Rome',
	'Europe/Samara',
	'Europe/San_Marino',
	'Europe/Sarajevo',
	'Europe/Saratov',
	'Europe/Simferopol',
	'Europe/Skopje',
	'Europe/Sofia',
	'Europe/Stockholm',
	'Europe/Tallinn',
	'Europe/Tirane',
	'Europe/Ulyanovsk',
	'Europe/Vaduz',
	'Europe/Vatican',
	'Europe/Vienna',
	'Europe/Vilnius',
	'Europe/Volgograd',
	'Europe/Warsaw',
	'Europe/Zagreb',
	'Europe/Zurich',
	'Indian/Antananarivo',
	'Indian/Chagos',
	'Indian/Christmas',
	'Indian/Cocos',
	'Indian/Comoro',
	'Indian/Kerguelen',
	'Indian/Mahe',
	'Indian/Maldives',
	'Indian/Mauritius',
	'Indian/Mayotte',
	'Indian/Reunion',
	'Pacific/Apia',
	'Pacific/Auckland',
	'Pacific/Bougainville',
	'Pacific/Chatham',
	'Pacific/Easter',
	'Pacific/Efate',
	'Pacific/Enderbury',
	'Pacific/Fakaofo',
	'Pacific/Fiji',
	'Pacific/Funafuti',
	'Pacific/Galapagos',
	'Pacific/Gambier',
	'Pacific/Guadalcanal',
	'Pacific/Guam',
	'Pacific/Honolulu',
	'Pacific/Kiritimati',
	'Pacific/Kosrae',
	'Pacific/Kwajalein',
	'Pacific/Majuro',
	'Pacific/Marquesas',
	'Pacific/Midway',
	'Pacific/Nauru',
	'Pacific/Niue',
	'Pacific/Norfolk',
	'Pacific/Noumea',
	'Pacific/Pago_Pago',
	'Pacific/Palau',
	'Pacific/Pitcairn',
	'Pacific/Ponape',
	'Pacific/Port_Moresby',
	'Pacific/Rarotonga',
	'Pacific/Saipan',
	'Pacific/Tahiti',
	'Pacific/Tarawa',
	'Pacific/Tongatapu',
	'Pacific/Truk',
	'Pacific/Wake',
	'Pacific/Wallis'
];
