<script lang="ts">
	import { DEFAULT_CURRENCY, formatMoney, toMoneyValue } from '$lib/money';

	export let price: number | string | null | undefined = null;
	export let currency: string | null | undefined = null;
	export let showIcon: boolean = true;
	export let badgeClass: string = 'badge-ghost badge-sm';

	$: priceLabel = formatMoney(toMoneyValue(price, currency, DEFAULT_CURRENCY));
</script>

{#if priceLabel}
	<span class="badge {badgeClass} whitespace-nowrap">
		{#if showIcon}💰{/if} {priceLabel}
	</span>
{/if}
