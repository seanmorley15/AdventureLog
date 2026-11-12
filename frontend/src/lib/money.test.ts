import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
	CURRENCY_OPTIONS,
	currencyName,
	formatMoney,
	normalizeMoneyPayload,
	toMoneyValue
} from './money';

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

describe('CURRENCY_OPTIONS', () => {
	it('offers exactly the currencies the backend accepts as a default currency', () => {
		const schema = readFileSync(
			join(import.meta.dirname, '../../../backend/server/openapi/schema.yaml'),
			'utf8'
		);
		const block = schema.split('    DefaultCurrencyEnum:\n')[1].split('      type: string')[0];
		const backend = [...block.matchAll(/^ {6}- ([A-Z]{3})$/gm)].map((match) => match[1]);
		expect(CURRENCY_OPTIONS).toEqual(backend);
	});

	it('has no duplicates', () => {
		expect(new Set(CURRENCY_OPTIONS).size).toBe(CURRENCY_OPTIONS.length);
	});
});

describe('currencyName', () => {
	it("names a currency in the reader's language", () => {
		expect(currencyName('COP', 'en')).toBe('Colombian Peso');
		expect(currencyName('COP', 'de')).toBe('Kolumbianischer Peso');
	});

	it('accepts app locales written with an underscore', () => {
		expect(currencyName('USD', 'zh_Hant')).not.toBe('USD');
	});

	it('falls back to the code for an unknown code or locale', () => {
		expect(currencyName('QQQ', 'en')).toBe('QQQ');
		expect(currencyName('not-a-code', 'en')).toBe('not-a-code');
		expect(currencyName('EUR', '!!')).toBe('Euro');
	});
});
