export type DateFormatPreference = 'locale' | 'mdy' | 'dmy' | 'ymd';

export const DEFAULT_DATE_FORMAT: DateFormatPreference = 'locale';

export const DATE_FORMAT_OPTIONS: DateFormatPreference[] = ['locale', 'mdy', 'dmy', 'ymd'];

export const DATE_FORMAT_LABELS: Record<DateFormatPreference, string> = {
	locale: 'Browser default',
	mdy: 'MM/DD/YYYY',
	dmy: 'DD/MM/YYYY',
	ymd: 'YYYY-MM-DD'
};

const PREFERENCE_LOCALES: Record<Exclude<DateFormatPreference, 'locale'>, string> = {
	mdy: 'en-US',
	dmy: 'en-GB',
	ymd: 'sv-SE' // ISO-like YYYY-MM-DD
};

function isDateFormatPreference(value: unknown): value is DateFormatPreference {
	return typeof value === 'string' && DATE_FORMAT_OPTIONS.includes(value as DateFormatPreference);
}

export function normalizeDateFormat(value: unknown): DateFormatPreference {
	return isDateFormatPreference(value) ? value : DEFAULT_DATE_FORMAT;
}

/** Resolve an Intl locale tag for the given preference. */
export function resolveDateFormatLocale(
	preference: DateFormatPreference = DEFAULT_DATE_FORMAT
): string {
	if (preference === 'locale') {
		if (typeof navigator !== 'undefined' && navigator.language) {
			return navigator.language;
		}
		return 'en-US';
	}
	return PREFERENCE_LOCALES[preference];
}

export function prefersHour12(preference: DateFormatPreference = DEFAULT_DATE_FORMAT): boolean {
	return preference === 'locale' || preference === 'mdy';
}

/** Format an HH:MM clock time using the user's date preference (12h or 24h). */
export function formatDisplayTime(
	time: string | null | undefined,
	preference: DateFormatPreference = DEFAULT_DATE_FORMAT
): string {
	if (!time) return '';
	const match = /^(\d{1,2}):(\d{2})/.exec(time);
	if (!match) return time;
	const hours = Number(match[1]);
	const minutes = Number(match[2]);
	if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return time;

	const date = new Date(2000, 0, 1, hours, minutes);
	try {
		return new Intl.DateTimeFormat(resolveDateFormatLocale(preference), {
			hour: 'numeric',
			minute: '2-digit',
			hour12: prefersHour12(preference)
		}).format(date);
	} catch {
		return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
	}
}

function parseDateOnly(iso: string): Date | null {
	if (!iso) return null;
	const datePart = iso.split('T')[0];
	if (!/^\d{4}-\d{2}-\d{2}$/.test(datePart)) return null;
	// Midday avoids DST/timezone day-shift for date-only values
	return new Date(`${datePart}T12:00:00`);
}

export type FormatDisplayDateOptions = {
	/** Force UTC for date-only calendar fields (notes/checklists). */
	timeZone?: string;
	month?: 'numeric' | '2-digit' | 'short' | 'long';
	year?: 'numeric' | '2-digit';
	day?: 'numeric' | '2-digit';
};

/** Format a date-only ISO string (YYYY-MM-DD or datetime truncated to date). */
export function formatDisplayDate(
	iso: string | null | undefined,
	preference: DateFormatPreference = DEFAULT_DATE_FORMAT,
	opts: FormatDisplayDateOptions = {}
): string {
	if (!iso) return '';
	const date = parseDateOnly(iso);
	if (!date || Number.isNaN(date.getTime())) return '';

	const locale = resolveDateFormatLocale(preference);
	try {
		return new Intl.DateTimeFormat(locale, {
			year: opts.year ?? 'numeric',
			month: opts.month ?? (preference === 'ymd' ? '2-digit' : 'short'),
			day: opts.day ?? (preference === 'ymd' ? '2-digit' : 'numeric'),
			timeZone: opts.timeZone
		}).format(date);
	} catch {
		return date.toLocaleDateString();
	}
}

/** Format a UTC datetime ISO string with optional timezone. */
export function formatDisplayDateTime(
	iso: string | null | undefined,
	preference: DateFormatPreference = DEFAULT_DATE_FORMAT,
	timezone?: string | null
): string {
	if (!iso) return '';
	try {
		const locale = resolveDateFormatLocale(preference);
		return new Intl.DateTimeFormat(locale, {
			timeZone: timezone || undefined,
			year: 'numeric',
			month: preference === 'ymd' ? '2-digit' : 'short',
			day: preference === 'ymd' ? '2-digit' : 'numeric',
			hour: '2-digit',
			minute: '2-digit',
			hour12: prefersHour12(preference)
		}).format(new Date(iso));
	} catch {
		return new Date(iso).toLocaleString();
	}
}

/**
 * First day of week for Cally: 0 = Sunday, 1 = Monday.
 * `locale` preference uses Intl.Locale weekInfo when available.
 */
export function getFirstDayOfWeek(preference: DateFormatPreference = DEFAULT_DATE_FORMAT): number {
	if (preference === 'mdy') return 0;
	if (preference === 'dmy' || preference === 'ymd') return 1;

	try {
		const localeTag = resolveDateFormatLocale(preference);
		const locale = new Intl.Locale(localeTag) as Intl.Locale & {
			weekInfo?: { firstDay?: number };
			getWeekInfo?: () => { firstDay?: number };
		};
		const info = locale.weekInfo ?? locale.getWeekInfo?.();
		// Intl uses 1=Monday … 7=Sunday; Cally uses 0=Sunday … 6=Saturday
		if (info?.firstDay != null) {
			return info.firstDay === 7 ? 0 : info.firstDay;
		}
	} catch {
		// fall through
	}
	return 1;
}

/** Preview string for settings UI (today in the chosen format). */
export function formatDateFormatPreview(preference: DateFormatPreference): string {
	const today = new Date();
	const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
	return formatDisplayDate(iso, preference, { month: '2-digit', day: '2-digit', year: 'numeric' });
}

/** Normalize preference from a user object (or guests). */
export function dateFormatFromUser(
	user: { date_format?: string } | null | undefined
): DateFormatPreference {
	return normalizeDateFormat(user?.date_format);
}

type DateOrder = 'mdy' | 'dmy' | 'ymd';

/** Field order (month/day/year) used when typing a date under the given preference. */
export function getDateOrder(preference: DateFormatPreference = DEFAULT_DATE_FORMAT): DateOrder {
	if (preference !== 'locale') return preference;
	try {
		const parts = new Intl.DateTimeFormat(resolveDateFormatLocale(preference)).formatToParts(
			new Date(2000, 10, 22)
		);
		const order = parts
			.filter((p) => p.type === 'month' || p.type === 'day' || p.type === 'year')
			.map((p) => p.type[0])
			.join('');
		if (order === 'mdy' || order === 'dmy' || order === 'ymd') return order;
	} catch {
		// fall through
	}
	return 'mdy';
}

/** Short placeholder such as "MM/DD/YYYY" matching what the field accepts. */
export function getDateInputHint(preference: DateFormatPreference = DEFAULT_DATE_FORMAT): string {
	const names = { m: 'MM', d: 'DD', y: 'YYYY' } as const;
	const sep = getDateOrder(preference) === 'ymd' ? '-' : '/';
	return [...getDateOrder(preference)].map((c) => names[c as 'm' | 'd' | 'y']).join(sep);
}

const MONTH_NAMES = [
	'jan',
	'feb',
	'mar',
	'apr',
	'may',
	'jun',
	'jul',
	'aug',
	'sep',
	'oct',
	'nov',
	'dec'
];

function toIsoDate(year: number, month: number, day: number): string | null {
	if (year < 1000 || year > 9999) return null;
	const d = new Date(Date.UTC(year, month - 1, day));
	if (d.getUTCFullYear() !== year || d.getUTCMonth() !== month - 1 || d.getUTCDate() !== day) {
		return null;
	}
	return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function expandYear(raw: string): number {
	const n = Number(raw);
	return raw.length <= 2 ? 2000 + n : n;
}

/**
 * Parse a hand-typed date into YYYY-MM-DD, or null if it isn't a valid date.
 * Accepts the user's preferred order with / . - or space separators, ISO dates,
 * compact digits (08032026), "Mar 8 2026" / "8 March 2026", and "today"/"yesterday".
 */
export function parseTypedDate(
	input: string,
	preference: DateFormatPreference = DEFAULT_DATE_FORMAT,
	today: Date = new Date()
): string | null {
	const text = input.trim().toLowerCase();
	if (!text) return null;

	if (text === 'today' || text === 'yesterday') {
		const d = new Date(today.getFullYear(), today.getMonth(), today.getDate());
		if (text === 'yesterday') d.setDate(d.getDate() - 1);
		return toIsoDate(d.getFullYear(), d.getMonth() + 1, d.getDate());
	}

	const order = getDateOrder(preference);

	// Month names: "8 mar 2026", "mar 8, 2026"
	let m = /^(\d{1,2})[\s.-]+([a-z]{3,})\.?,?[\s.-]+(\d{2}|\d{4})$/.exec(text);
	if (m) {
		const month = MONTH_NAMES.indexOf(m[2].slice(0, 3)) + 1;
		return month ? toIsoDate(expandYear(m[3]), month, Number(m[1])) : null;
	}
	m = /^([a-z]{3,})\.?[\s.-]+(\d{1,2}),?[\s.-]+(\d{2}|\d{4})$/.exec(text);
	if (m) {
		const month = MONTH_NAMES.indexOf(m[1].slice(0, 3)) + 1;
		return month ? toIsoDate(expandYear(m[3]), month, Number(m[2])) : null;
	}

	let parts: string[] | null = null;
	let partsOrder: DateOrder = order;

	if (/^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$/.test(text)) {
		parts = text.split(/[-/.]/);
		partsOrder = 'ymd';
	} else if (/^\d{8}$/.test(text)) {
		// 20260308 reads as ISO; otherwise follow the user's order
		if (/^(19|20)\d{2}(0[1-9]|1[0-2])/.test(text) || order === 'ymd') {
			parts = [text.slice(0, 4), text.slice(4, 6), text.slice(6, 8)];
			partsOrder = 'ymd';
		} else {
			parts = [text.slice(0, 2), text.slice(2, 4), text.slice(4)];
		}
	} else if (/^\d{1,2}[-/.\s]\d{1,2}[-/.\s](\d{2}|\d{4})$/.test(text)) {
		parts = text.split(/[-/.\s]/);
		if (order === 'ymd') partsOrder = 'dmy';
	}

	if (!parts) return null;
	const [a, b, c] = parts;
	if (partsOrder === 'ymd') return toIsoDate(Number(a), Number(b), Number(c));
	if (partsOrder === 'mdy') return toIsoDate(expandYear(c), Number(a), Number(b));
	return toIsoDate(expandYear(c), Number(b), Number(a));
}
