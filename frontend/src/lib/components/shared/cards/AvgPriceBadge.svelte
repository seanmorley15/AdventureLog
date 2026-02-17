<script lang="ts">
	import { formatMoney } from '$lib/money';
	import type { DerivedPrice } from '$lib/types';
	import { formatConvertedPrice, ratesLoaded } from '$lib/stores/exchangeRates';

	export let avgPricePerUser: DerivedPrice | null | undefined = null;
	export let avgPricePerUserPerNight: DerivedPrice | null | undefined = null;
	export let countryCurrency: string | null = null;
	export let userCurrency: string | null = null;
	export let showIcon: boolean = true;
	export let badgeClass: string = 'badge-success badge-sm';

	// Use per-night if available (lodging), otherwise per-user
	$: derivedPrice = avgPricePerUserPerNight || avgPricePerUser;

	// Primary: country currency (or original if no country)
	$: primaryPrice = (() => {
		if (!derivedPrice) return null;
		const originalCurrency = derivedPrice.currency;
		if ($ratesLoaded && countryCurrency && countryCurrency !== originalCurrency) {
			return formatConvertedPrice(derivedPrice.amount, originalCurrency, countryCurrency);
		}
		return formatMoney({ amount: derivedPrice.amount, currency: originalCurrency });
	})();

	// Secondary: user currency (if different from country currency)
	$: secondaryPrice = (() => {
		if (!derivedPrice || !$ratesLoaded || !userCurrency) return null;
		const originalCurrency = derivedPrice.currency;
		// Don't show if user currency is same as country currency or original
		if (userCurrency === countryCurrency || userCurrency === originalCurrency) return null;
		return formatConvertedPrice(derivedPrice.amount, originalCurrency, userCurrency);
	})();
</script>

{#if primaryPrice}
	<span class="badge {badgeClass} whitespace-nowrap">
		{#if showIcon}💰{/if} {primaryPrice}
		{#if secondaryPrice}
			<span class="opacity-70 text-xs">({secondaryPrice})</span>
		{/if}
	</span>
{/if}
