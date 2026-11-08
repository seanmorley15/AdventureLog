import { describe, expect, it } from 'vitest';
import { formatMoney, normalizeMoneyPayload, toMoneyValue } from './money';

describe('toMoneyValue', () => {
	it('parses numeric strings and numbers', () => {
		expect(toMoneyValue('12.5', 'EUR')).toEqual({ amount: 12.5, currency: 'EUR' });
		expect(toMoneyValue(7, 'GBP')).toEqual({ amount: 7, currency: 'GBP' });
	});

	it('treats NaN and undefined as no amount', () => {
		expect(toMoneyValue('abc', 'USD').amount).toBeNull();
		expect(toMoneyValue(undefined, 'USD').amount).toBeNull();
	});

	it('keeps null as null', () => {
		expect(toMoneyValue(null, 'USD').amount).toBeNull();
	});

	it('falls back to the default currency when blank or not a string', () => {
		expect(toMoneyValue(1, '').currency).toBe('USD');
		expect(toMoneyValue(1, '   ').currency).toBe('USD');
		expect(toMoneyValue(1, null).currency).toBe('USD');
		expect(toMoneyValue(1, undefined, 'JPY').currency).toBe('JPY');
	});
});

describe('normalizeMoneyPayload', () => {
	it('coerces a string amount to a number and keeps the currency', () => {
		expect(normalizeMoneyPayload({ price: '19.99', price_currency: 'EUR', name: 'x' })).toEqual({
			price: 19.99,
			price_currency: 'EUR',
			name: 'x'
		});
	});

	it('fills in the fallback currency', () => {
		expect(normalizeMoneyPayload({ price: 5 }).price_currency).toBe('USD');
		expect(
			normalizeMoneyPayload({ price: 5, price_currency: '' }, 'price', 'price_currency', 'CAD')
		).toMatchObject({ price_currency: 'CAD' });
	});

	it('drops both fields when there is no usable amount', () => {
		for (const price of [null, undefined, 'nope']) {
			const result = normalizeMoneyPayload({ price, price_currency: 'EUR', name: 'x' });
			expect(result).toEqual({ name: 'x' });
		}
	});

	it('does not mutate its input', () => {
		const input = { price: null, price_currency: 'EUR' };
		normalizeMoneyPayload(input);
		expect(input).toEqual({ price: null, price_currency: 'EUR' });
	});

	it('supports custom field names', () => {
		expect(
			normalizeMoneyPayload({ cost: '3', cost_currency: 'USD' }, 'cost', 'cost_currency')
		).toEqual({
			cost: 3,
			cost_currency: 'USD'
		});
	});
});

describe('formatMoney', () => {
	it('formats with the locale and currency', () => {
		expect(formatMoney({ amount: 1234.5, currency: 'USD' })).toBe('$1,234.50');
		expect(formatMoney({ amount: 10, currency: 'EUR' }, 'de-DE')).toBe('10,00 €');
	});

	it('returns null without an amount or currency', () => {
		expect(formatMoney({ amount: null, currency: 'USD' })).toBeNull();
		expect(formatMoney({ amount: 5, currency: null })).toBeNull();
	});

	it('falls back to a plain string for an invalid currency code', () => {
		expect(formatMoney({ amount: 5, currency: 'not-a-code' })).toBe('not-a-code 5');
	});
});
