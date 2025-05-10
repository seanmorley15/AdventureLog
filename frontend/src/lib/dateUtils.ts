// @ts-ignore
import { DateTime } from 'luxon';

/**
 * Convert a UTC ISO date to a datetime-local value in the specified timezone
 * @param utcDate - UTC date in ISO format or null
 * @param timezone - Target timezone (defaults to browser timezone)
 * @returns Formatted local datetime string for input fields (YYYY-MM-DDTHH:MM)
 */
export function toLocalDatetime(
	utcDate: string | null,
	timezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone
): string {
	if (!utcDate) return '';
	return DateTime.fromISO(utcDate, { zone: 'UTC' })
		.setZone(timezone)
		.toISO({ suppressSeconds: true, includeOffset: false })
		.slice(0, 16);
}

/**
 * Convert a local datetime to UTC
 * @param localDate - Local datetime string in ISO format
 * @param timezone - Source timezone (defaults to browser timezone)
 * @returns UTC datetime in ISO format or null
 */
export function toUTCDatetime(
	localDate: string,
	timezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone,
	allDay: boolean = false
): string | null {
	if (!localDate) return null;

	if (allDay) {
		// Treat input as date-only, set UTC midnight manually
		return DateTime.fromISO(localDate, { zone: 'UTC' })
			.startOf('day')
			.toISO({ suppressMilliseconds: true });
	}

	// Normal timezone conversion for datetime-local input
	return DateTime.fromISO(localDate, { zone: timezone })
		.toUTC()
		.toISO({ suppressMilliseconds: true });
}

/**
 * Updates local datetime values based on UTC date and timezone
 * @param params Object containing UTC date and timezone
 * @returns Object with updated local datetime string
 */
export function updateLocalDate({
	utcDate,
	timezone
}: {
	utcDate: string | null;
	timezone: string;
}) {
	return {
		localDate: toLocalDatetime(utcDate, timezone)
	};
}

/**
 * Updates UTC datetime values based on local datetime and timezone
 * @param params Object containing local date and timezone
 * @returns Object with updated UTC datetime string
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
	return {
		utcDate: toUTCDatetime(localDate, timezone, allDay)
	};
}

/**
 * Validate date ranges
 * @param startDate - Start date string
 * @param endDate - End date string
 * @returns Object with validation result and error message
 */
export function validateDateRange(
	startDate: string,
	endDate: string
): { valid: boolean; error?: string } {
	if (endDate && !startDate) {
		return {
			valid: false,
			error: 'Start date is required when end date is provided'
		};
	}

	if (
		startDate &&
		endDate &&
		DateTime.fromISO(startDate).toMillis() > DateTime.fromISO(endDate).toMillis()
	) {
		return {
			valid: false,
			error: 'Start date must be before end date'
		};
	}

	return { valid: true };
}

/**
 * Format UTC date for display
 * @param utcDate - UTC date in ISO format
 * @returns Formatted date string without seconds (YYYY-MM-DD HH:MM)
 */
export function formatUTCDate(utcDate: string | null): string {
	if (!utcDate) return '';
	return DateTime.fromISO(utcDate).toISO().slice(0, 16).replace('T', ' ');
}
