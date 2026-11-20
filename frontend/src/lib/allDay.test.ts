import { describe, expect, it } from 'vitest';
import { isAllDayEntry } from './index';

describe('isAllDayEntry', () => {
	it('treats midnight UTC with no time zone as a date without a time', () => {
		expect(isAllDayEntry('2026-10-29T00:00:00Z', null)).toBe(true);
		expect(isAllDayEntry('2026-10-29T00:00:00+00:00', undefined)).toBe(true);
	});

	it('keeps a timed entry at 00:00 UTC timed when it has a zone (#1327)', () => {
		// 8:00 PM in New York on 28 October 2026
		expect(isAllDayEntry('2026-10-29T00:00:00Z', 'America/New_York')).toBe(false);
	});

	it('is false for other times and for no date', () => {
		expect(isAllDayEntry('2026-10-29T09:30:00Z', null)).toBe(false);
		expect(isAllDayEntry(null, null)).toBe(false);
		expect(isAllDayEntry('', null)).toBe(false);
	});
});
