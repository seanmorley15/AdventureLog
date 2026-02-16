import type { MoneyValue } from './types';

export const DEFAULT_CURRENCY = 'USD';

export const CURRENCY_METADATA: { code: string; label: string }[] = [
	// Major currencies
	{ code: 'USD', label: 'US Dollar' },
	{ code: 'EUR', label: 'Euro' },
	{ code: 'GBP', label: 'British Pound' },
	{ code: 'JPY', label: 'Japanese Yen' },
	{ code: 'CHF', label: 'Swiss Franc' },
	// Americas
	{ code: 'CAD', label: 'Canadian Dollar' },
	{ code: 'MXN', label: 'Mexican Peso' },
	{ code: 'BRL', label: 'Brazilian Real' },
	{ code: 'ARS', label: 'Argentine Peso' },
	{ code: 'CLP', label: 'Chilean Peso' },
	{ code: 'COP', label: 'Colombian Peso' },
	{ code: 'PEN', label: 'Peruvian Sol' },
	// Asia-Pacific
	{ code: 'CNY', label: 'Chinese Yuan' },
	{ code: 'HKD', label: 'Hong Kong Dollar' },
	{ code: 'SGD', label: 'Singapore Dollar' },
	{ code: 'AUD', label: 'Australian Dollar' },
	{ code: 'NZD', label: 'New Zealand Dollar' },
	{ code: 'INR', label: 'Indian Rupee' },
	{ code: 'KRW', label: 'South Korean Won' },
	{ code: 'THB', label: 'Thai Baht' },
	{ code: 'IDR', label: 'Indonesian Rupiah' },
	{ code: 'MYR', label: 'Malaysian Ringgit' },
	{ code: 'PHP', label: 'Philippine Peso' },
	{ code: 'VND', label: 'Vietnamese Dong' },
	{ code: 'TWD', label: 'Taiwan Dollar' },
	// Europe
	{ code: 'SEK', label: 'Swedish Krona' },
	{ code: 'NOK', label: 'Norwegian Krone' },
	{ code: 'DKK', label: 'Danish Krone' },
	{ code: 'PLN', label: 'Polish Zloty' },
	{ code: 'CZK', label: 'Czech Koruna' },
	{ code: 'HUF', label: 'Hungarian Forint' },
	{ code: 'RON', label: 'Romanian Leu' },
	{ code: 'ISK', label: 'Icelandic Krona' },
	{ code: 'TRY', label: 'Turkish Lira' },
	{ code: 'RUB', label: 'Russian Ruble' },
	{ code: 'UAH', label: 'Ukrainian Hryvnia' },
	// Middle East & Africa
	{ code: 'AED', label: 'UAE Dirham' },
	{ code: 'SAR', label: 'Saudi Riyal' },
	{ code: 'ILS', label: 'Israeli Shekel' },
	{ code: 'ZAR', label: 'South African Rand' },
	{ code: 'EGP', label: 'Egyptian Pound' },
	{ code: 'MAD', label: 'Moroccan Dirham' },
	{ code: 'KES', label: 'Kenyan Shilling' },
	{ code: 'NGN', label: 'Nigerian Naira' },
	// Others
	{ code: 'XPF', label: 'CFP Franc' },
	{ code: 'XOF', label: 'West African CFA' },
	{ code: 'XAF', label: 'Central African CFA' }
];

export const CURRENCY_OPTIONS = CURRENCY_METADATA.map(({ code }) => code);
export const CURRENCY_LABELS = Object.fromEntries(
	CURRENCY_METADATA.map(({ code, label }) => [code, label])
);

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
