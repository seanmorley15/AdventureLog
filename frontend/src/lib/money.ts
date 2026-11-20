import type { MoneyValue } from './types';

export const DEFAULT_CURRENCY = 'USD';

/**
 * The currencies people choose from: those in circulation (ISO 4217), the most used first.
 * The backend's users.models.CURRENCY_CHOICES has the same codes; money.test.ts checks that they
 * match. Names come from the browser, in the reader's language (see currencyName).
 */
export const CURRENCY_OPTIONS: string[] = [
	'USD',
	'EUR',
	'GBP',
	'JPY',
	'AUD',
	'CAD',
	'CHF',
	'CNY',
	'HKD',
	'SGD',
	'SEK',
	'NOK',
	'DKK',
	'NZD',
	'INR',
	'MXN',
	'BRL',
	'ZAR',
	'AED',
	'TRY',
	'AFN',
	'ALL',
	'AMD',
	'AOA',
	'ARS',
	'AWG',
	'AZN',
	'BAM',
	'BBD',
	'BDT',
	'BGN',
	'BHD',
	'BIF',
	'BMD',
	'BND',
	'BOB',
	'BSD',
	'BTN',
	'BWP',
	'BYN',
	'BZD',
	'CDF',
	'CLP',
	'COP',
	'CRC',
	'CUP',
	'CVE',
	'CZK',
	'DJF',
	'DOP',
	'DZD',
	'EGP',
	'ERN',
	'ETB',
	'FJD',
	'FKP',
	'GEL',
	'GHS',
	'GIP',
	'GMD',
	'GNF',
	'GTQ',
	'GYD',
	'HNL',
	'HTG',
	'HUF',
	'IDR',
	'ILS',
	'IQD',
	'IRR',
	'ISK',
	'JMD',
	'JOD',
	'KES',
	'KGS',
	'KHR',
	'KMF',
	'KPW',
	'KRW',
	'KWD',
	'KYD',
	'KZT',
	'LAK',
	'LBP',
	'LKR',
	'LRD',
	'LSL',
	'LYD',
	'MAD',
	'MDL',
	'MGA',
	'MKD',
	'MMK',
	'MNT',
	'MOP',
	'MRU',
	'MUR',
	'MVR',
	'MWK',
	'MYR',
	'MZN',
	'NAD',
	'NGN',
	'NIO',
	'NPR',
	'OMR',
	'PAB',
	'PEN',
	'PGK',
	'PHP',
	'PKR',
	'PLN',
	'PYG',
	'QAR',
	'RON',
	'RSD',
	'RUB',
	'RWF',
	'SAR',
	'SBD',
	'SCR',
	'SDG',
	'SHP',
	'SLE',
	'SOS',
	'SRD',
	'SSP',
	'STN',
	'SVC',
	'SYP',
	'SZL',
	'THB',
	'TJS',
	'TMT',
	'TND',
	'TOP',
	'TTD',
	'TWD',
	'TZS',
	'UAH',
	'UGX',
	'UYU',
	'UZS',
	'VES',
	'VND',
	'VUV',
	'WST',
	'XAF',
	'XCD',
	'XOF',
	'XPF',
	'YER',
	'ZMW'
];

const displayNames = new Map<string, Intl.DisplayNames | null>();

/** The currency's name in an app locale such as `de` or `zh_Hant`, or its code when unknown. */
export function currencyName(code: string, locale?: string | null): string {
	const tag = (locale || 'en').replace('_', '-');
	if (!displayNames.has(tag)) {
		let names: Intl.DisplayNames | null = null;
		// A locale the browser cannot parse falls back to English names.
		for (const tags of [[tag, 'en'], ['en']]) {
			try {
				names = new Intl.DisplayNames(tags, { type: 'currency' });
				break;
			} catch {
				// try the next
			}
		}
		displayNames.set(tag, names);
	}
	try {
		return displayNames.get(tag)?.of(code) ?? code;
	} catch {
		return code;
	}
}

export function toMoneyValue(
	price: unknown,
	currency: unknown,
	fallback: string = DEFAULT_CURRENCY
): MoneyValue {
	const amount = typeof price === 'string' ? Number(price) : (price as number | null);
	const safeAmount = amount === undefined || Number.isNaN(amount) ? null : amount;
	const safeCurrency = typeof currency === 'string' && currency.trim() ? currency : fallback;
	return {
		amount: safeAmount,
		currency: safeCurrency || null
	};
}

export function normalizeMoneyPayload(
	payload: Record<string, any>,
	field: string = 'price',
	currencyField: string = 'price_currency',
	fallback: string = DEFAULT_CURRENCY
): Record<string, any> {
	const amountRaw = payload[field];
	const currencyRaw = payload[currencyField];
	const amount = typeof amountRaw === 'string' ? Number(amountRaw) : amountRaw;
	const hasAmount = amount !== null && amount !== undefined && !Number.isNaN(Number(amount));

	if (!hasAmount) {
		const clean = { ...payload };
		delete clean[field];
		delete clean[currencyField];
		return clean;
	}

	return {
		...payload,
		[field]: Number(amount),
		[currencyField]: currencyRaw || fallback
	};
}

export function formatMoney(value: MoneyValue, locale: string = 'en-US'): string | null {
	if (value.amount === null || value.amount === undefined || !value.currency) return null;
	try {
		return new Intl.NumberFormat(locale, {
			style: 'currency',
			currency: value.currency,
			maximumFractionDigits: 2
		}).format(value.amount);
	} catch (_e) {
		return `${value.currency} ${value.amount}`;
	}
}
