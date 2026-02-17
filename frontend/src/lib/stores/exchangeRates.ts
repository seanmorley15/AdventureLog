import { writable, derived, get } from 'svelte/store';

// Exchange rates with USD as base currency
export const exchangeRates = writable<Record<string, number>>({});
export const ratesLoading = writable(false);
export const ratesLoaded = writable(false);

// Derived store: list of available currency codes (sorted)
export const availableCurrencies = derived(exchangeRates, ($rates) => {
	return Object.keys($rates).sort();
});

/**
 * Fetch all exchange rates from the API
 * Rates are relative to USD (base currency)
 */
export async function fetchExchangeRates(): Promise<void> {
	// Skip if already loaded or loading
	if (get(ratesLoaded) || get(ratesLoading)) {
		return;
	}

	ratesLoading.set(true);

	try {
		const res = await fetch('/api/exchange-rates/all_rates/');
		if (res.ok) {
			const data = await res.json();
			exchangeRates.set(data);
			ratesLoaded.set(true);
		}
	} catch (error) {
		console.error('Error fetching exchange rates:', error);
	} finally {
		ratesLoading.set(false);
	}
}

/**
 * Convert amount from one currency to another
 * @param amount - The amount to convert
 * @param fromCurrency - Source currency code (e.g., 'EUR')
 * @param toCurrency - Target currency code (e.g., 'USD')
 * @returns Converted amount or null if conversion not possible
 */
export function convertCurrency(
	amount: number,
	fromCurrency: string,
	toCurrency: string
): number | null {
	if (fromCurrency === toCurrency) {
		return amount;
	}

	const rates = get(exchangeRates);
	if (Object.keys(rates).length === 0) {
		return null;
	}

	// Get rates relative to USD
	const fromRate = fromCurrency === 'USD' ? 1.0 : rates[fromCurrency];
	const toRate = toCurrency === 'USD' ? 1.0 : rates[toCurrency];

	if (!fromRate || !toRate) {
		return null;
	}

	// Convert: amount -> USD -> target
	const amountInUsd = amount / fromRate;
	return amountInUsd * toRate;
}

/**
 * Format a converted price for display
 * @param amount - Original amount
 * @param fromCurrency - Original currency
 * @param toCurrency - Target currency for display
 * @returns Formatted string like "~$25.00" or null if conversion not possible
 */
export function formatConvertedPrice(
	amount: number,
	fromCurrency: string,
	toCurrency: string
): string | null {
	const converted = convertCurrency(amount, fromCurrency, toCurrency);
	if (converted === null) {
		return null;
	}

	// Format with currency symbol
	try {
		const formatted = new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: toCurrency,
			minimumFractionDigits: 0,
			maximumFractionDigits: 2
		}).format(converted);
		return `~${formatted}`;
	} catch {
		return `~${converted.toFixed(2)} ${toCurrency}`;
	}
}
