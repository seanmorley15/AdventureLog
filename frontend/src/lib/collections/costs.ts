import type { Collection } from '#lib/types.js';
import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '#lib/money.js';

export type CostCategory = 'lodging' | 'transportation' | 'location';

export type CostEntry = {
	currency: string;
	amount: number;
	category: CostCategory;
};

export type CurrencyBreakdown = {
	currency: string;
	total: number;
	formattedTotal: string;
	categories: Array<{
		category: CostCategory;
		label: string;
		total: number;
		count: number;
		formattedTotal: string;
	}>;
};

export function buildCostEntries(
	current: Collection | null,
	fallbackCurrency: string
): CostEntry[] {
	if (!current) return [];
	const entries: CostEntry[] = [];
	const fallback = fallbackCurrency || DEFAULT_CURRENCY;

	const push = (
		price: number | string | null | undefined,
		priceCurrency: string | null | undefined,
		category: CostCategory
	) => {
		const moneyValue = toMoneyValue(price, priceCurrency, fallback);
		if (moneyValue.amount === null || moneyValue.amount === undefined) return;
		entries.push({
			currency: moneyValue.currency || fallback,
			amount: moneyValue.amount,
			category
		});
	};

	for (const item of current.locations ?? []) push(item.price, item.price_currency, 'location');
	for (const item of current.transportations ?? [])
		push(item.price, item.price_currency, 'transportation');
	for (const item of current.lodging ?? []) push(item.price, item.price_currency, 'lodging');

	return entries;
}

export function summarizeCostEntries(
	entries: CostEntry[],
	locale: string,
	labels: Record<CostCategory, string>
): CurrencyBreakdown[] {
	const currencyBuckets: Record<
		string,
		{ total: number; categories: Record<CostCategory, { total: number; count: number }> }
	> = {};

	for (const { currency, amount, category } of entries) {
		if (amount === null || amount === undefined || Number.isNaN(amount)) continue;
		const safeCurrency = currency || DEFAULT_CURRENCY;
		currencyBuckets[safeCurrency] ??= {
			total: 0,
			categories: {} as Record<CostCategory, { total: number; count: number }>
		};

		const bucket = currencyBuckets[safeCurrency];
		bucket.total += amount;
		bucket.categories[category] ??= { total: 0, count: 0 };
		bucket.categories[category].total += amount;
		bucket.categories[category].count += 1;
	}

	const format = (value: number, currency: string) =>
		formatMoney({ amount: value, currency }, locale) || `${currency} ${value}`;

	return Object.entries(currencyBuckets)
		.map(([currency, data]) => ({
			currency,
			total: data.total,
			formattedTotal: format(data.total, currency),
			categories: Object.entries(data.categories).map(([categoryKey, info]) => {
				const category = categoryKey as CostCategory;
				return {
					category,
					label: labels[category],
					total: info.total,
					count: info.count,
					formattedTotal: format(info.total, currency)
				};
			})
		}))
		.sort((a, b) => a.currency.localeCompare(b.currency));
}
